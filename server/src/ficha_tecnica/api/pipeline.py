"""The analysis pipeline (section 5.3): from pasted text to a reading sheet.

Order of work, and why:

1. The blackout window is checked first, locally and cheaply. Inside it only group B is
   asked (is this electoral?), so a refused story costs one call instead of three.
2. Outside the window groups A and B are asked **concurrently**, because NaN allows two
   requests in flight and those are exactly the two slots.
3. Group C is asked only when the text both claims to quote the questions and Clef is
   confident it does.
4. Item states come from the policy table, the semaphore from 7.4 plus the arithmetic.

Item states that ask for a second reading are shown as ``review`` for now: ENC-12 adds the
focused second call. Showing "we are not sure" is the honest interim behaviour, and it is
the direction the design asks for anyway.
"""

import asyncio
import hashlib
import time
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from ficha_tecnica.clef_client import DecisionProvider
from ficha_tecnica.clef_client.models import (
    ChoiceAnswer,
    ClefResponse,
    NoulAnswer,
    Question,
)
from ficha_tecnica.extractor.candidates import all_candidates
from ficha_tecnica.extractor.digest import (
    build_digest_a,
    build_digest_b,
    build_digest_c,
    build_focused_digest,
    build_state,
)
from ficha_tecnica.extractor.entities import find_estimates
from ficha_tecnica.extractor.metrics import extract_confidence, extract_margin, extract_sample_size
from ficha_tecnica.extractor.normalize import strip_paste_artifacts
from ficha_tecnica.extractor.numbers import parse_spanish_number
from ficha_tecnica.policy import (
    ItemDecision,
    ItemState,
    PolicyConfig,
    assign_semaphore,
    decide_item,
    finalize_item,
    fired_rules,
    group_b_flags,
    resolve_now,
    should_block,
    veda_notice,
    within_window,
)
from ficha_tecnica.policy.calculator import lead_ratio, theoretical_margin
from ficha_tecnica.sanitizer import mask_vote_estimates
from ficha_tecnica.schema.checklist import load_checklist
from ficha_tecnica.schema.questionnaire import Questionnaire, load_questionnaire
from ficha_tecnica.schema.report import (
    Computation,
    Finding,
    ItemStatus,
    Report,
    Severity,
    Source,
    Span,
)

DISCLAIMER = (
    "No es asesoramiento jurídico: la valoración corresponde a la Junta Electoral Central. "
    "Esta ficha describe la información que da la noticia, no la calidad de la encuesta."
)

MESSAGES = {
    "present": "El texto aporta este dato.",
    "absent": "El texto no aporta este dato.",
    "refers_external": "El texto remite a una ficha técnica publicada en otro sitio.",
    "review": "No estamos seguros con este punto: conviene revisarlo a mano.",
}

#: SECOND_READING has no message of its own: it is shown as review until ENC-12 exists.
_SEVERITY: dict[str, Severity] = {
    "high": "high",
    "medium": "medium",
    "low": "low",
    "note": "note",
}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _probability(answer: object) -> float | None:
    if isinstance(answer, NoulAnswer | ChoiceAnswer):
        return answer.yes_probability()
    return None


def _lead(text: str) -> Decimal | None:
    """Difference between the two highest figures cited next to a formation."""
    figures: list[Decimal] = []
    for span in find_estimates(text):
        figure = parse_spanish_number(text[span.start : span.end].rstrip(" %"))
        if figure is not None:
            figures.append(figure)
    if len(figures) < 2:
        return None
    ordered = sorted(figures, reverse=True)
    return ordered[0] - ordered[1]


async def analyze(
    text: str,
    *,
    provider: DecisionProvider,
    policy: PolicyConfig,
    now: datetime | None = None,
    provider_name: str = "mock",
    calls: list[dict[str, object]] | None = None,
) -> Report:
    """Run one analysis and return the sheet. Never stores or returns the input text."""
    started = time.perf_counter()
    if not text.strip():
        raise ValueError("text must not be empty")

    # Fences and other paste artifacts are blanked, never deleted: every span the caller
    # gets back must still point at the same character of the text it pasted.
    text = strip_paste_artifacts(text)

    checklist = load_checklist()
    questionnaire = load_questionnaire()
    candidates = all_candidates(text)
    moment = now or resolve_now(policy.veda)
    digest_a = build_digest_a(text)
    digest_b = build_digest_b(text)
    digest_c = build_digest_c(text)

    inside_window = within_window(moment, policy.veda)
    if inside_window:
        # Only group B is needed to decide whether the story is electoral at all, so a
        # refused story costs one call instead of three.
        answers_b = (await _ask(provider, digest_b, _group(questionnaire, "B"), "B", calls)).answers
        poll_type, poll_type_probs = _poll_type(answers_b)
        is_electoral = _probability(answers_b.get("b_is_electoral"))
        if should_block(
            when=moment, is_electoral=is_electoral, poll_type=poll_type, veda=policy.veda
        ):
            return _veda_report(policy, provider_name, started, text)
        answers_a = (await _ask(provider, digest_a, _group(questionnaire, "A"), "A", calls)).answers
    else:
        # NaN allows two requests in flight and these are exactly the two slots. Group B is
        # asked once, not twice: it answers both the framing questions and the blackout one.
        response_a, response_b = await asyncio.gather(
            _ask(provider, digest_a, _group(questionnaire, "A"), "A", calls),
            _ask(provider, digest_b, _group(questionnaire, "B"), "B", calls),
        )
        answers_a = response_a.answers
        answers_b = response_b.answers
        poll_type, poll_type_probs = _poll_type(answers_b)
        is_electoral = _probability(answers_b.get("b_is_electoral"))

    quoted = digest_c["quoted_questions"]
    if quoted and (_probability(answers_a.get("a_question_text")) or 0.0) >= 0.80:
        await _ask(provider, digest_c, _group(questionnaire, "C"), "C", calls)

    external = _probability(answers_a.get("a_external_sheet"))
    states: dict[str, tuple[float | None, bool, ItemState]] = {}
    for item in checklist.items:
        probability = _probability(answers_a.get(item.id))
        has_candidate = bool(candidates.get(item.id))
        state = decide_item(
            item_id=item.id,
            layer=item.layer,
            has_candidate=has_candidate,
            probability=probability if probability is not None else 0.0,
            policy=policy,
            external_sheet_probability=external,
        )
        states[item.id] = (probability, has_candidate, state)

    doubts = [
        item_id for item_id, (_, _, state) in states.items() if state == "needs_second_reading"
    ]
    if doubts:
        states.update(
            await _second_reading(text, doubts, states, provider, questionnaire, policy, calls)
        )

    findings: list[Finding] = []
    decisions: list[ItemDecision] = []
    for item in checklist.items:
        probability, has_candidate, state = states[item.id]
        shown: ItemStatus = "review" if state == "needs_second_reading" else state  # type: ignore[assignment]
        decisions.append(
            ItemDecision(
                item_id=item.id,
                layer=item.layer,
                weight=item.weight,
                state=shown,  # type: ignore[arg-type]
            )
        )
        findings.append(
            Finding(
                item_id=item.id,
                layer=item.layer,
                status=shown,
                severity=_SEVERITY[item.weight],
                source=_source(has_candidate, shown),
                probability=probability,
                evidence=[
                    Span(start=span.start, end=span.end) for span in candidates.get(item.id, [])
                ],
                message=mask_vote_estimates(MESSAGES[shown]),
            )
        )

    computation, arithmetic_flags = _computation(text, answers_b, policy)
    fired = arithmetic_flags | group_b_flags(
        headline_overreach_score=_score(answers_b.get("b_headline_overreach")),
        prediction_probability=_probability(answers_b.get("b_prediction")),
        subgroup_probability=_probability(answers_b.get("b_subgroup")),
        self_selected_probability=_self_selected(answers_b, poll_type),
        policy=policy,
    )

    return Report(
        id=uuid4().hex,
        created_at=moment.isoformat(),
        text_hash=_hash(text),
        checklist_version=checklist.version,
        questionnaire_version=questionnaire.version,
        provider=provider_name,  # type: ignore[arg-type]
        poll_type=poll_type,
        poll_type_probs=poll_type_probs,
        semaphore=assign_semaphore(
            decisions, fired=frozenset(fired), policy=policy, poll_type=poll_type
        ),
        status="ok",
        findings=findings,
        computation=computation,
        disclaimer=DISCLAIMER,
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


async def _second_reading(
    text: str,
    doubts: list[str],
    states: dict[str, tuple[float | None, bool, ItemState]],
    provider: DecisionProvider,
    questionnaire: Questionnaire,
    policy: PolicyConfig,
    calls: list[dict[str, object]] | None,
) -> dict[str, tuple[float | None, bool, ItemState]]:
    """Re-ask only the items in doubt, with a state reduced to their evidence.

    A second look that cannot improve the answer is money wasted, so the questions are
    narrowed to the doubtful items and the rest of the sheet keeps its first answer.
    """
    focused = build_focused_digest(text, doubts)
    questions = {
        question_id: question
        for question_id, question in _group(questionnaire, "A").items()
        if question_id in doubts
    }
    if not questions:
        return {}
    answers = (await _ask(provider, focused, questions, "focused", calls)).answers

    updated: dict[str, tuple[float | None, bool, ItemState]] = {}
    for item_id in doubts:
        _, has_candidate, _ = states[item_id]
        probability = _probability(answers.get(item_id))
        if probability is None:
            updated[item_id] = (states[item_id][0], has_candidate, "review")
            continue
        updated[item_id] = (
            probability,
            has_candidate,
            finalize_item(has_candidate=has_candidate, probability=probability, policy=policy),
        )
    return updated


def _veda_report(policy: PolicyConfig, provider_name: str, started: float, text: str) -> Report:
    return Report(
        id=uuid4().hex,
        created_at=resolve_now(policy.veda).isoformat(),
        text_hash=_hash(text),
        checklist_version=load_checklist().version,
        questionnaire_version=load_questionnaire().version,
        provider=provider_name,  # type: ignore[arg-type]
        poll_type="not_a_poll",
        semaphore="grey",
        status="veda",
        findings=[],
        computation=None,
        disclaimer=f"{veda_notice(policy.veda)} {DISCLAIMER}",
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


async def _ask(
    provider: DecisionProvider,
    digest: dict,
    questions: dict[str, Question],
    group: str,
    calls: list[dict[str, object]] | None,
) -> ClefResponse:
    """Ask one group and, when a collector is given, record probabilities only.

    The digest is deliberately never recorded: section 9 keeps the analysis, not the story.
    """
    started = time.perf_counter()
    response = await provider.ask(build_state(digest), questions)
    if calls is not None:
        calls.append(
            {
                "group_name": group,
                "model": "clef",
                "tokens_in": response.usage.input_tokens,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "raw_answers": {
                    question_id: {
                        "type": answer.type,
                        "probabilities": dict(answer.probabilities),
                    }
                    for question_id, answer in response.answers.items()
                },
            }
        )
    return response


def _group(questionnaire: Questionnaire, name: str) -> dict[str, Question]:
    """The questions of one group, keyed by checklist id."""
    return {question.id: question.payload for question in questionnaire.groups[name]}


def _poll_type(answers: dict) -> tuple[str, dict[str, float]]:
    answer = answers.get("b_poll_type")
    if isinstance(answer, ChoiceAnswer):
        return answer.choice, dict(answer.probabilities)
    return "not_a_poll", {}


def _score(answer: object) -> float | None:
    from ficha_tecnica.clef_client.models import ScoreAnswer

    return answer.score if isinstance(answer, ScoreAnswer) else None


def _self_selected(answers: dict, poll_type: str) -> float | None:
    if poll_type == "self_selected_online_poll":
        answer = answers.get("b_poll_type")
        if isinstance(answer, ChoiceAnswer):
            return answer.probabilities.get("self_selected_online_poll")
    return None


def _source(has_candidate: bool, status: ItemStatus) -> Source:
    if status == "present":
        return "both" if has_candidate else "clef"
    if status == "refers_external":
        return "clef"
    return "code" if has_candidate else "clef"


def _computation(text: str, answers_b: dict, policy: PolicyConfig) -> tuple[Computation, set[str]]:
    sample_size = extract_sample_size(text)
    declared = extract_margin(text)
    confidence = extract_confidence(text)
    lead = _lead(text)
    decisive = _probability(answers_b.get("b_lead_decisive"))

    theory: Decimal | None = None
    if sample_size is not None:
        theory = theoretical_margin(sample_size, confidence=confidence)

    fired = fired_rules(
        sample_size=sample_size,
        declared_margin=declared,
        lead=lead,
        lead_decisive_probability=decisive,
        confidence=confidence,
        policy=policy,
    )

    ratio: Decimal | None = None
    if declared is not None and lead is not None:
        try:
            ratio = lead_ratio(lead, declared)
        except ValueError:  # pragma: no cover - declared is positive when parsed
            ratio = None

    return (
        Computation(
            sample_size=sample_size,
            declared_margin=float(declared) if declared is not None else None,
            theoretical_margin=float(theory) if theory is not None else None,
            lead_ratio=float(ratio) if ratio is not None else None,
        ),
        fired,
    )
