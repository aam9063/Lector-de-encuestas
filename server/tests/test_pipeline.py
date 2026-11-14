"""ENC-11: the analysis pipeline end to end, with the mock provider.

High risk is in the invariants, not the wiring: the report must never carry a
vote-estimate figure, never name a formation, and every evidence span must point into the
text the user pasted.
"""

import json

import pytest

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.clef_client import MockProvider
from ficha_tecnica.clef_client.models import ChoiceAnswer, NoulAnswer
from ficha_tecnica.policy import load_policy
from ficha_tecnica.sanitizer import find_leaks

NEWS = (
    "SIMULACION. El Partido Popular ganaria las elecciones segun una encuesta de "
    "Demoscopia Ficticia S.L. realizada por encargo del diario El Ejemplo. "
    "El estudio se hizo con 1.200 entrevistas entre el 3 y el 9 de noviembre. "
    "El margen de error es de 2,8 puntos para un nivel de confianza del 95 %. "
    "El Partido Popular obtendria un 32 % de los votos y el PSOE un 28 %."
)

PARTY_NAMES = ("Partido Popular", "PSOE", "Vox", "Sumar", "Ciudadanos", "ERC", "Junts")


class Sampler:
    """A provider whose answers the test controls, item by item."""

    def __init__(self, noul: dict[str, float], poll_type: str = "direct_voting_intention") -> None:
        self._noul = noul
        self._poll_type = poll_type

    async def ask(self, state: str, questions):
        from ficha_tecnica.clef_client.models import ClefResponse, Diagnostic, Usage

        answers = {}
        for question_id, question in questions.items():
            if question.type == "noul":
                yes = self._noul.get(question_id, 0.5)
                answers[question_id] = NoulAnswer(
                    type="noul", noul=yes, probabilities={"yes": yes, "no": 1 - yes}, confidence=yes
                )
            elif question.type == "choice":
                labels = list(question.criteria)
                share = 1.0 / len(labels)
                answers[question_id] = ChoiceAnswer(
                    type="choice",
                    choice=self._poll_type if self._poll_type in labels else labels[0],
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


async def test_the_report_covers_every_checklist_item(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)

    assert len(report.findings) == 15
    assert report.checklist_version == 1
    assert report.questionnaire_version == 1
    assert report.provider == "mock"


async def test_a_present_item_with_strong_evidence_is_present(policy) -> None:
    provider = Sampler({"a_sample_size": 0.95, "a_margin": 0.95, "a_is_electoral": 0.95})

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_sample_size"].status == "present"
    assert by_id["a_margin"].status == "present"
    assert by_id["a_sample_size"].probability == pytest.approx(0.95)


async def test_an_item_in_doubt_ends_in_review_without_a_second_reading(policy) -> None:
    """ENC-12 adds the focused second reading; until then a doubt is shown as review."""
    provider = Sampler({"a_entity_address": 0.45, "a_margin": 0.30})

    report = await analyze(NEWS, provider=provider, policy=policy)
    by_id = {finding.item_id: finding for finding in report.findings}

    assert by_id["a_entity_address"].status == "review"
    assert by_id["a_margin"].status == "review"


async def test_evidence_spans_point_into_the_input_text(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)

    for finding in report.findings:
        for span in finding.evidence:
            assert 0 <= span.start < span.end <= len(NEWS)
            assert NEWS[span.start : span.end].strip()


async def test_the_serialized_report_never_leaks_a_vote_estimate(policy) -> None:
    provider = Sampler({"a_sample_size": 0.95, "a_margin": 0.95, "b_is_electoral": 0.95})

    report = await analyze(NEWS, provider=provider, policy=policy)
    serialized = report.model_dump_json()

    assert find_leaks(serialized) == []
    assert "32 %" not in serialized
    assert "34,2" not in serialized


async def test_the_report_never_names_a_formation(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)
    serialized = report.model_dump_json()

    for name in PARTY_NAMES:
        assert name not in serialized, f"report names {name}"


async def test_the_arithmetic_lands_in_the_report(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)

    assert report.computation is not None
    assert report.computation.sample_size == 1200
    assert report.computation.declared_margin == pytest.approx(2.8)
    assert report.computation.theoretical_margin == pytest.approx(2.8)


async def test_inside_the_blackout_window_the_report_is_a_notice(policy, monkeypatch) -> None:
    monkeypatch.setenv("VEDA_NOW", "2026-11-25T10:00:00+01:00")
    provider = Sampler({"b_is_electoral": 0.95})

    report = await analyze(NEWS, provider=provider, policy=policy)

    assert report.status == "veda"
    assert report.findings == []
    assert report.semaphore == "grey"
    assert "veda" in report.disclaimer.lower()


async def test_a_non_electoral_topic_is_analysed_inside_the_window(policy, monkeypatch) -> None:
    monkeypatch.setenv("VEDA_NOW", "2026-11-25T10:00:00+01:00")
    provider = Sampler({"b_is_electoral": 0.02}, poll_type="issue_opinion")

    report = await analyze(
        "SIMULACION. Encuesta sobre la calidad del transporte publico con 1.200 entrevistas.",
        provider=provider,
        policy=policy,
    )

    assert report.status == "ok"
    assert report.findings


async def test_the_semaphore_is_grey_when_the_text_is_not_a_poll(policy) -> None:
    provider = Sampler({"b_is_electoral": 0.01}, poll_type="not_a_poll")

    report = await analyze(
        "SIMULACION. Una receta de tortilla con 2 huevos y 1 patata.",
        provider=provider,
        policy=policy,
    )

    assert report.status == "ok"
    assert report.semaphore == "grey"


async def test_an_empty_text_is_rejected(policy) -> None:
    with pytest.raises(ValueError, match="text"):
        await analyze("   ", provider=MockProvider(), policy=policy)


async def test_the_report_disclaimer_always_mentions_the_jec(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)

    assert "Junta Electoral Central" in report.disclaimer


def test_the_report_model_has_no_field_for_the_news_text() -> None:
    """A field that does not exist cannot be filled by accident."""
    from ficha_tecnica.schema.report import Report

    forbidden = {"text", "input_text", "body", "content", "news", "raw_text", "digest"}
    assert forbidden.isdisjoint(Report.model_fields), sorted(forbidden & set(Report.model_fields))
    assert "text_hash" in Report.model_fields


async def test_the_report_carries_a_hash_and_not_the_text(policy) -> None:
    report = await analyze(NEWS, provider=MockProvider(), policy=policy)

    assert len(report.text_hash) == 64
    assert NEWS[:40] not in json.dumps(report.model_dump())
