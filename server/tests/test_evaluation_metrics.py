"""ENC-17: metrics of the evaluation harness and what its output must respect.

The unit fixtures are hand-built judgments; the end-to-end cases run the real
harness over a sliver of the corpus with the offline mock provider, which is also
the model for the leak counter (it must stay at zero) and for the B1/B2 rows
(unavailable with a reason, never simulated).
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.clef_client import MockProvider
from ficha_tecnica.evaluation.baselines import run_baseline, unavailable_baseline
from ficha_tecnica.evaluation.dataset import build_dataset
from ficha_tecnica.evaluation.metrics import (
    CaseJudgment,
    GoldLabel,
    calibration_error,
    f1_by_item,
    false_accusation_rate,
    omission_recall,
    percentile,
    review_fraction,
    rule_accuracy,
    stability,
)
from ficha_tecnica.evaluation.render import render_chart_svg, render_table
from ficha_tecnica.evaluation.runner import run_harness
from ficha_tecnica.policy import load_policy
from ficha_tecnica.sanitizer import find_leaks

NOW = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)


def judgment(
    case_id: str = "case-1",
    mutation: str = "base",
    gold: Mapping[str, GoldLabel] | None = None,
    statuses: dict[str, str] | None = None,
    probabilities: dict[str, float | None] | None = None,
    expected_flags: frozenset[str] = frozenset(),
    latency_ms: int = 100,
) -> CaseJudgment:
    return CaseJudgment(
        case_id=case_id,
        mutation=mutation,
        gold=gold or {},
        statuses=statuses or {},
        probabilities=probabilities or {},
        expected_flags=expected_flags,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------- false accusation


def test_false_accusation_counts_only_items_whose_gold_is_present():
    one = judgment(
        gold={"a_margin": "present", "a_client": "present", "a_mode": "absent"},
        statuses={"a_margin": "absent", "a_client": "present", "a_mode": "present"},
    )

    metric = false_accusation_rate([one])

    # a_mode is wrongly "present", but its gold is absent: it never counts here.
    assert metric.numerator == 1
    assert metric.denominator == 2
    assert metric.value == pytest.approx(0.5)


def test_false_accusation_with_no_present_gold_is_not_a_zero_that_lies():
    one = judgment(gold={"a_mode": "absent"}, statuses={"a_mode": "present"})

    assert false_accusation_rate([one]).denominator == 0
    assert false_accusation_rate([one]).value is None


# ---------------------------------------------------------------- recall, review


def test_omission_recall_counts_the_absent_gold_items_that_were_reported_absent():
    one = judgment(
        gold={"a_margin": "absent", "a_client": "absent", "a_mode": "present"},
        statuses={"a_margin": "absent", "a_client": "review", "a_mode": "present"},
    )

    metric = omission_recall([one])

    assert metric.numerator == 1
    assert metric.denominator == 2
    assert metric.value == pytest.approx(0.5)


def test_review_fraction_uses_every_judged_item():
    one = judgment(
        gold={"a": "present", "b": "absent", "c": "present"},
        statuses={"a": "review", "b": "absent", "c": "present"},
    )

    assert review_fraction([one]).value == pytest.approx(1 / 3)


# ---------------------------------------------------------------- f1 per item


def test_f1_per_item_is_computed_from_present_vs_not_present():
    cases = [
        judgment(
            gold={"a_margin": "present", "a_client": "present", "a_mode": "absent"},
            statuses={"a_margin": "present", "a_client": "absent", "a_mode": "absent"},
        ),
        judgment(
            gold={"a_margin": "present", "a_client": "absent", "a_mode": "absent"},
            statuses={"a_margin": "present", "a_client": "present", "a_mode": "review"},
        ),
    ]

    table = f1_by_item(cases)

    # a_margin: 2 true positives, nothing else -> perfect F1.
    assert table["a_margin"] is not None
    assert table["a_margin"].f1 == pytest.approx(1.0)
    # a_client: one false negative, one false positive and no true positive -> all 0.
    assert table["a_client"] is not None
    assert table["a_client"].precision == pytest.approx(0.0)
    assert table["a_client"].recall == pytest.approx(0.0)
    assert table["a_client"].f1 == pytest.approx(0.0)
    # a_mode: gold never present and never detected -> the F1 is undefined, not zero.
    assert table["a_mode"] is None


# ---------------------------------------------------------------- arithmetic fidelity


def test_rule_accuracy_compares_expected_flags_with_the_code_verdict():
    cases = [
        judgment(case_id="c1", expected_flags=frozenset({"M4"})),
        judgment(case_id="c2"),
        judgment(case_id="c3"),
    ]
    fired = {"c1": {"M4"}, "c2": set(), "c3": {"M5"}}

    accuracy = rule_accuracy(cases, fired)

    assert accuracy["M4"].value == pytest.approx(1.0)
    # M5 must not fire here, and c3 is a case where it did: one miss in three.
    assert accuracy["M5"].value == pytest.approx(2 / 3)


# ---------------------------------------------------------------- calibration


def test_calibration_error_is_zero_when_the_probability_matches_the_gold():
    cases = [
        judgment(gold={"a": "present"}, statuses={"a": "present"}, probabilities={"a": 1.0}),
        judgment(gold={"a": "absent"}, statuses={"a": "absent"}, probabilities={"a": 0.0}),
    ]

    assert calibration_error(cases).value == pytest.approx(0.0)


def test_calibration_error_penalises_confident_mistakes():
    cases = [
        judgment(gold={"a": "absent"}, statuses={"a": "absent"}, probabilities={"a": 0.99}),
    ]

    assert calibration_error(cases).value == pytest.approx(0.99)


def test_calibration_ignores_items_without_a_probability():
    cases = [
        judgment(gold={"a": "present"}, statuses={"a": "present"}, probabilities={"a": None}),
    ]

    assert calibration_error(cases).denominator == 0
    assert calibration_error(cases).value is None


# ---------------------------------------------------------------- latency


def test_percentiles_use_the_nearest_rank_definition():
    latencies = [40, 10, 30, 20]

    assert percentile(latencies, 50) == 20
    assert percentile(latencies, 95) == 40
    assert percentile([], 50) is None


# ---------------------------------------------------------------- stability


def test_stability_compares_two_runs_item_by_item():
    first = [
        judgment(statuses={"a": "present", "b": "review"}),
        judgment(statuses={"a": "absent", "c": "present"}),
    ]
    second = [
        judgment(statuses={"a": "present", "b": "absent"}),
        judgment(statuses={"a": "absent", "c": "present"}),
    ]

    assert stability(first, second) == pytest.approx(3 / 4)


# ---------------------------------------------------------------- baselines


def test_b1_and_b2_are_reported_unavailable_with_a_reason_never_simulated():
    for baseline in ("B1", "B2"):
        run = unavailable_baseline(baseline)
        assert run.judgments == ()
        assert run.unavailable_reason
        assert "unavailable" in run.unavailable_reason.lower()


# ---------------------------------------------------------------- the new pipeline flag


def _m1_case():
    dataset = build_dataset()
    return next(case for case in dataset.all_cases if case.mutation == "M1")


async def test_b3_single_reading_never_makes_the_focused_call():
    case = _m1_case()
    calls: list[dict[str, object]] = []

    report = await analyze(
        case.text,
        provider=MockProvider(),
        policy=load_policy(),
        now=NOW,
        calls=calls,
        second_reading=False,
    )

    group_names = [str(call["group_name"]) for call in calls]
    assert "focused" not in group_names
    by_id = {finding.item_id: finding for finding in report.findings}
    # The removed item stays an honest "we are not sure".
    assert by_id["a_sample_size"].status == "review"


async def test_the_default_behaviour_still_runs_the_second_reading():
    case = _m1_case()
    calls: list[dict[str, object]] = []

    await analyze(
        case.text,
        provider=MockProvider(),
        policy=load_policy(),
        now=NOW,
        calls=calls,
    )

    group_names = [str(call["group_name"]) for call in calls]
    assert group_names[-1] == "focused"


# ---------------------------------------------------------------- end to end


async def test_the_harness_runs_a_sliver_of_corpus_through_three_baselines(tmp_path: Path):
    report = await run_harness(
        baselines=("B0", "B3", "B4"),
        split="test",
        limit=2,
        provider=MockProvider(),
        provider_name="mock",
    )

    assert report.provider_name == "mock"
    assert report.cases_considered == 2
    ids = {row.baseline for row in report.rows}
    assert ids == {"B0", "B3", "B4"}
    for row in report.rows:
        assert row.false_accusation.denominator > 0
        assert row.latency_p50_ms is not None

    table = render_table(report)
    assert "| B0 |" in table and "| B3 |" in table and "| B4 |" in table
    assert find_leaks(table) == []

    svg = render_chart_svg(report)
    assert svg.startswith("<svg")
    assert find_leaks(svg) == []


async def test_the_harness_reports_a_zero_leak_count():
    report = await run_harness(
        baselines=("B0", "B4"),
        split="test",
        limit=2,
        provider=MockProvider(),
        provider_name="mock",
    )

    assert report.leak_count == 0


async def test_unavailable_baselines_end_in_the_report_with_their_reason():
    report = await run_harness(
        baselines=("B1",),
        split="test",
        limit=2,
        provider=MockProvider(),
        provider_name="mock",
    )

    assert len(report.rows) == 1
    assert report.rows[0].unavailable_reason
    assert report.rows[0].false_accusation.value is None


async def test_stability_of_the_full_system_is_measured_by_rerunning():
    dataset = build_dataset()
    run = await run_baseline(
        "B4",
        dataset.all_cases[:2],
        provider=MockProvider(),
        provider_name="mock",
        now=NOW,
    )

    assert run.stability is not None
    assert run.stability.value == pytest.approx(1.0)
