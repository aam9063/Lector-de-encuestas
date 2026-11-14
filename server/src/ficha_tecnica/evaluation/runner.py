"""The harness orchestrator: dataset in, one scored row per baseline out.

Cost discipline comes from the caller: ``--limit`` bounds the number of cases, and
the default is small so that nobody fires hundreds of API calls by accident. The
stability metric reruns every case once, which doubles the calls; it is a defined
metric of section 11.3, not an option.

Leak counting covers every free-text output the harness produces, which is the
rendered table and the SVG chart; per-item messages come from the pipeline, where
they are fixed templates already masked by the sanitizer.
"""

import time
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from ficha_tecnica.clef_client import DecisionProvider, MockProvider
from ficha_tecnica.evaluation.baselines import (
    ALL_BASELINES,
    code_rules_fired,
    run_baseline,
    unavailable_baseline,
)
from ficha_tecnica.evaluation.dataset import build_dataset
from ficha_tecnica.evaluation.metrics import (
    MetricValue,
    calibration_error,
    f1_by_item,
    false_accusation_rate,
    omission_recall,
    percentile,
    review_fraction,
    rule_accuracy,
)
from ficha_tecnica.evaluation.render import render_chart_svg, render_table
from ficha_tecnica.evaluation.rows import BaselineRow, HarnessReport
from ficha_tecnica.sanitizer import find_leaks

_UNAVAILABLE_BASELINES = ("B1", "B2")

#: The evaluation instant: well away from the blackout window, so a run in late
#: November does not silently measure veda mode instead of the baselines.
EVAL_INSTANT = datetime(2026, 6, 15, 10, 0, tzinfo=ZoneInfo("UTC"))


def _unavailable_row(baseline: str) -> BaselineRow:
    return BaselineRow(
        baseline=baseline,
        false_accusation=MetricValue(None),
        omission_recall=MetricValue(None),
        review_fraction=MetricValue(None),
        ece=MetricValue(None),
        case_count=0,
        unavailable_reason=unavailable_baseline(baseline).unavailable_reason,
    )


def _row(baseline: str, run, cases) -> BaselineRow:
    if run.unavailable_reason is not None:
        return _unavailable_row(baseline)
    judgments = run.judgments
    fired = {case.case_id: code_rules_fired(case.text) for case in cases}
    accuracy = rule_accuracy(judgments, fired)
    latencies = [judgment.latency_ms for judgment in judgments]
    return BaselineRow(
        baseline=baseline,
        false_accusation=false_accusation_rate(judgments),
        omission_recall=omission_recall(judgments),
        review_fraction=review_fraction(judgments),
        ece=calibration_error(judgments),
        case_count=len(judgments),
        m4=accuracy["M4"],
        m5=accuracy["M5"],
        stability=run.stability,
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        f1=dict(f1_by_item(judgments)),
    )


async def run_harness(
    baselines: tuple[str, ...],
    *,
    split: str = "test",
    limit: int = 6,
    provider: DecisionProvider | None = None,
    provider_name: str = "mock",
    now: datetime | None = None,
    notes: tuple[str, ...] = (),
) -> HarnessReport:
    """Run the selected baselines over the first ``limit`` cases of one split."""
    for baseline in baselines:
        if baseline not in ALL_BASELINES:
            raise ValueError(f"unknown baseline {baseline!r}")

    dataset = build_dataset()
    cases = tuple(case for case in dataset.all_cases if case.split == split)[:limit]
    resolved_provider = provider or MockProvider()
    resolved_now = now or EVAL_INSTANT

    rows: list[BaselineRow] = []
    for baseline in baselines:
        if baseline in _UNAVAILABLE_BASELINES:
            rows.append(_unavailable_row(baseline))
            continue
        started = time.perf_counter()
        run = await run_baseline(
            baseline,
            cases,
            provider=resolved_provider,
            provider_name=provider_name,
            now=resolved_now,
        )
        rows.append(_row(baseline, run, cases))
        del started  # per-case latency already lives in the judgments

    first = HarnessReport(
        provider_name=provider_name,
        rows=tuple(rows),
        cases_considered=len(cases),
        leak_count=0,
        notes=notes,
    )
    table = render_table(first)
    chart = render_chart_svg(first)
    leak_count = len(find_leaks(table)) + len(find_leaks(chart))
    return replace(first, leak_count=leak_count, table=table, chart=chart)
