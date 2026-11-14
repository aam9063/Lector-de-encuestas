"""Baselines B0..B4 of section 11.2, measured over the same pipeline.

- **B0** is rules and regular expressions only: an item is ``present`` exactly when the
  code layer finds a candidate sentence, and the arithmetic rules run with no LLM input
  (without Clef there is no "lead is decisive" answer, so M5 cannot fire).
- **B3** is the single-reading system: the pipeline runs with ``second_reading=False``,
  so an item in doubt stays ``review`` and no focused call is ever made.
- **B4** is the complete system: the pipeline with its focused second reading.
- **B1/B2** are the NaN-LLM judges of the design. This harness only speaks the Clef
  decision API, so there is no chat model to judge with; they are reported as
  ``unavailable`` with a reason and are never simulated.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.clef_client import DecisionProvider
from ficha_tecnica.evaluation.dataset import EvalCase
from ficha_tecnica.evaluation.metrics import CaseJudgment, MetricValue, stability
from ficha_tecnica.extractor.candidates import all_candidates
from ficha_tecnica.extractor.entities import find_estimates
from ficha_tecnica.extractor.metrics import (
    extract_confidence,
    extract_margin,
    extract_sample_size,
)
from ficha_tecnica.extractor.numbers import parse_spanish_number
from ficha_tecnica.policy import PolicyConfig, fired_rules, load_policy

AVAILABLE_BASELINES = ("B0", "B3", "B4")
ALL_BASELINES = ("B0", "B1", "B2", "B3", "B4")

UNAVAILABLE_REASON = (
    "unavailable: the harness has no chat-model access, only the Clef decision API; "
    "the LLM judges of section 11.2 are out of scope and are never simulated"
)


@dataclass(frozen=True)
class BaselineRun:
    """What one baseline produced over one set of cases."""

    baseline: str
    judgments: tuple[CaseJudgment, ...]
    stability: MetricValue | None = None
    unavailable_reason: str | None = None


def unavailable_baseline(baseline: str) -> BaselineRun:
    """B1/B2 as an honest hole in the table, with the reason attached."""
    return BaselineRun(baseline=baseline, judgments=(), unavailable_reason=UNAVAILABLE_REASON)


def code_rules_fired(text: str) -> set[str]:
    """M4/M5 as the pure-code component would fire them, with no probabilities."""
    sample_size = extract_sample_size(text)
    margin = extract_margin(text)
    confidence = extract_confidence(text)

    lead: Decimal | None = None
    figures: list[Decimal] = []
    for span in find_estimates(text):
        figure = parse_spanish_number(text[span.start : span.end].rstrip(" %"))
        if figure is not None:
            figures.append(figure)
    if len(figures) >= 2:
        ordered = sorted(figures, reverse=True)
        lead = ordered[0] - ordered[1]

    return fired_rules(
        sample_size=sample_size,
        declared_margin=margin,
        lead=lead,
        # Without Clef there is no "the lead is decisive" answer, so M5 cannot fire:
        # the code component alone never accuses a headline of overreach.
        lead_decisive_probability=None,
        confidence=confidence,
        policy=load_policy(),
    )


def _b0_judgment(case: EvalCase) -> CaseJudgment:
    started = time.perf_counter()
    candidates = all_candidates(case.text)
    statuses = {item_id: "present" if found else "absent" for item_id, found in candidates.items()}
    latency = int((time.perf_counter() - started) * 1000)
    return CaseJudgment(
        case_id=case.case_id,
        mutation=case.mutation,
        gold=case.gold.items,
        statuses=statuses,
        probabilities={},
        expected_flags=case.gold.expected_flags,
        latency_ms=latency,
    )


async def _clef_judgment(
    case: EvalCase,
    provider: DecisionProvider,
    policy: PolicyConfig,
    now: datetime | None,
    provider_name: str,
    *,
    second_reading: bool,
) -> CaseJudgment:
    report = await analyze(
        case.text,
        provider=provider,
        policy=policy,
        now=now,
        provider_name=provider_name,  # type: ignore[arg-type]
        second_reading=second_reading,
    )
    return CaseJudgment(
        case_id=case.case_id,
        mutation=case.mutation,
        gold=case.gold.items,
        statuses={finding.item_id: finding.status for finding in report.findings},
        probabilities={finding.item_id: finding.probability for finding in report.findings},
        expected_flags=case.gold.expected_flags,
        latency_ms=report.latency_ms,
    )


async def run_baseline(
    baseline: str,
    cases: Sequence[EvalCase],
    *,
    provider: DecisionProvider | None = None,
    provider_name: str = "mock",
    now: datetime | None = None,
    policy: PolicyConfig | None = None,
    compute_stability: bool = True,
) -> BaselineRun:
    """Run one baseline over the cases. B0 needs no provider at all."""
    resolved_policy = policy or load_policy()
    judgments: list[CaseJudgment] = []
    if baseline == "B0":
        judgments = [_b0_judgment(case) for case in cases]
    elif baseline in ("B3", "B4"):
        if provider is None:
            raise ValueError(f"{baseline} needs a decision provider")
        second_reading = baseline == "B4"
        judgments = [
            await _clef_judgment(
                case,
                provider,
                resolved_policy,
                now,
                provider_name,
                second_reading=second_reading,
            )
            for case in cases
        ]
    else:
        raise ValueError(f"unknown baseline {baseline!r}")

    stability_metric: MetricValue | None = None
    if compute_stability and cases:
        rerun: list[CaseJudgment] = []
        if baseline == "B0":
            rerun = [_b0_judgment(case) for case in cases]
        else:
            assert provider is not None
            for case in cases:
                rerun.append(
                    await _clef_judgment(
                        case,
                        provider,
                        resolved_policy,
                        now,
                        provider_name,
                        second_reading=baseline == "B4",
                    )
                )
        agreement = stability(judgments, rerun)
        if agreement is not None:
            ordered_total = sum(len(judgment.statuses) for judgment in judgments)
            stable = round(agreement * ordered_total)
            stability_metric = MetricValue(agreement, stable, ordered_total)
    return BaselineRun(baseline=baseline, judgments=tuple(judgments), stability=stability_metric)
