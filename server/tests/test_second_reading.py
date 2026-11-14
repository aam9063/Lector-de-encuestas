"""ENC-12: the focused second reading for grey-zone items (section 6.4).

A doubt is not a verdict. When the first pass leaves a formal item between "yes" and "no",
the same group is asked again with a smaller state: only that item's candidate sentences
and their immediate context. If the doubt survives, the item is shown as review.

The second call is expensive, so it must not happen when nobody is in doubt.
"""

import pytest

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.clef_client.models import (
    ChoiceAnswer,
    ClefResponse,
    Diagnostic,
    NoulAnswer,
    Usage,
)
from ficha_tecnica.extractor.digest import build_focused_digest, build_state, estimate_tokens
from ficha_tecnica.policy import load_policy

NEWS = (
    "SIMULACION. El Partido Popular ganaria las elecciones segun una encuesta de "
    "Demoscopia Ficticia S.L. El estudio se hizo con 1.200 entrevistas entre el 3 y el 9 "
    "de noviembre. El margen de error es de 2,8 puntos. La sede del instituto esta en "
    "Madrid. El Partido Popular obtendria un 32 % y el PSOE un 28 %."
)


class Scripted:
    """Answers the first pass from ``first`` and any repeat from ``second``."""

    def __init__(
        self,
        first: dict[str, float],
        second: dict[str, float] | None = None,
        poll_type: str = "direct_voting_intention",
    ) -> None:
        self._first = first
        self._second = second or {}
        self._seen: set[str] = set()
        self._poll_type = poll_type
        self.calls: list[list[str]] = []

    async def ask(self, state: str, questions):
        self.calls.append(list(questions))
        answers = {}
        for question_id, question in questions.items():
            if question.type == "noul":
                if question_id in self._second and question_id in self._seen:
                    yes = self._second[question_id]
                else:
                    yes = self._first.get(question_id, 0.5)
                    self._seen.add(question_id)
                answers[question_id] = NoulAnswer(
                    type="noul",
                    noul=yes,
                    probabilities={"yes": yes, "no": 1 - yes},
                    confidence=yes,
                )
            elif question.type == "choice":
                labels = list(question.criteria)
                share = 1.0 / len(labels)
                chosen = self._poll_type if self._poll_type in labels else labels[0]
                answers[question_id] = ChoiceAnswer(
                    type="choice",
                    choice=chosen,
                    probabilities=dict.fromkeys(labels, share),
                    confidence=share,
                )
        return ClefResponse(
            id="decision-test",
            object="structured_decision",
            created=0,
            model="clef",
            answers=answers,
            usage=Usage(input_tokens=100, output_tokens=0),
            diagnostics={
                question_id: Diagnostic(label_mass=1.0, argmax_is_label=True)
                for question_id in answers
            },
            joint=None,
        )


@pytest.fixture
def policy():
    return load_policy()


def test_the_focused_digest_carries_the_evidence_and_its_context() -> None:
    focused = build_focused_digest(NEWS, ["a_margin"])

    serialized = build_state(focused)
    assert "margen de error es de 2,8 puntos" in serialized
    # Immediate context: the sentence before is what usually says who ran the poll.
    assert "entrevistas" in serialized


def test_the_focused_digest_only_covers_the_requested_items() -> None:
    focused = build_focused_digest(NEWS, ["a_margin"])

    assert [item["id"] for item in focused["items"]] == ["a_margin"]


def test_the_focused_digest_is_smaller_than_the_full_one(policy) -> None:
    focused = build_focused_digest(NEWS, ["a_margin", "a_sample_size"])

    assert estimate_tokens(build_state(focused)) <= 600


def test_an_item_without_evidence_still_gets_a_focused_state() -> None:
    focused = build_focused_digest(NEWS, ["a_nonresponse"])

    assert focused["items"][0]["evidence"] == []
    assert focused["meta"]["chars"] > 0


async def test_a_confirmed_doubt_becomes_present(policy) -> None:
    provider = Scripted(
        first={"a_entity_address": 0.45},
        second={"a_entity_address": 0.92},
    )

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_entity_address"].status == "present"
    assert by_id["a_entity_address"].probability == pytest.approx(0.92)


async def test_a_doubt_confirmed_as_absent_becomes_absent(policy) -> None:
    provider = Scripted(
        first={"a_universe": 0.45},
        second={"a_universe": 0.04},
    )

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_universe"].status == "absent"


async def test_a_surviving_doubt_ends_in_review(policy) -> None:
    provider = Scripted(
        first={"a_entity_address": 0.45},
        second={"a_entity_address": 0.48},
    )

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_entity_address"].status == "review"


async def test_the_second_reading_asks_only_the_items_in_doubt(policy) -> None:
    provider = Scripted(
        first={"a_entity_address": 0.45, "a_margin": 0.95, "a_sample_size": 0.95},
        second={"a_entity_address": 0.92},
    )

    await analyze(NEWS, provider=provider, policy=policy)
    second_call = provider.calls[-1]

    assert "a_entity_address" in second_call
    assert "a_margin" not in second_call
    assert "a_sample_size" not in second_call
    assert len(second_call) < 15


async def test_no_doubt_means_no_second_reading(policy) -> None:
    everything_present = {item: 0.95 for item in _all_item_ids(policy)}
    provider = Scripted(first=everything_present)

    await analyze(NEWS, provider=provider, policy=policy)

    # One call for B, one for A: nothing else.
    assert len(provider.calls) == 2


async def test_a_methodological_doubt_goes_to_review_without_asking_again(policy) -> None:
    provider = Scripted(
        first={"a_weighting": 0.45},
        second={"a_weighting": 0.95},
    )

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_weighting"].status == "review"
    assert all("a_weighting" not in call for call in provider.calls[2:])


def _all_item_ids(policy) -> list[str]:
    from ficha_tecnica.schema.checklist import load_checklist

    return [item.id for item in load_checklist().items]
