"""Metrics of the evaluation harness (section 11.3).

Two asymmetries to keep straight, because they are the whole point of the exercise:

- the false-accusation rate counts, and only counts, items whose gold is ``present``
  but the system reported ``absent``. A wrong "present" on a truly absent item is a
  recall problem, never a false accusation;
- ``review`` is never an accusation and never a confirmation: it counts towards the
  review fraction, and it counts as a miss for the F1 of that item, nothing more.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

CaseId = str
#: The gold vocabulary of the corpus: labels are derived, never written.
GoldLabel = Literal["present", "absent"]
ItemStatus = str


@dataclass(frozen=True)
class MetricValue:
    """A ratio plus its counts, so no reader has to trust a bare percentage."""

    value: float | None
    numerator: int = 0
    denominator: int = 0


@dataclass(frozen=True)
class ItemF1:
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class CaseJudgment:
    """One case as one baseline saw it, ready to be scored against its gold."""

    case_id: str
    mutation: str
    gold: Mapping[str, GoldLabel]
    statuses: Mapping[str, ItemStatus]
    probabilities: Mapping[str, float | None] = field(default_factory=dict)
    expected_flags: frozenset[str] = frozenset()
    latency_ms: int = 0


def false_accusation_rate(judgments: Sequence[CaseJudgment]) -> MetricValue:
    """Share of gold-``present`` items reported ``absent``: the costliest mistake."""
    numerator = 0
    denominator = 0
    for judgment in judgments:
        for item_id, gold in judgment.gold.items():
            if gold != "present":
                continue
            denominator += 1
            if judgment.statuses.get(item_id) == "absent":
                numerator += 1
    if denominator == 0:
        return MetricValue(None)
    return MetricValue(numerator / denominator, numerator, denominator)


def omission_recall(judgments: Sequence[CaseJudgment]) -> MetricValue:
    """Share of truly absent items the system actually reported as absent."""
    numerator = 0
    denominator = 0
    for judgment in judgments:
        for item_id, gold in judgment.gold.items():
            if gold != "absent":
                continue
            denominator += 1
            if judgment.statuses.get(item_id) == "absent":
                numerator += 1
    if denominator == 0:
        return MetricValue(None)
    return MetricValue(numerator / denominator, numerator, denominator)


def review_fraction(judgments: Sequence[CaseJudgment]) -> MetricValue:
    """Share of judged items left as ``review`` (objective: at most 20 %)."""
    numerator = 0
    denominator = 0
    for judgment in judgments:
        for status in judgment.statuses.values():
            denominator += 1
            if status == "review":
                numerator += 1
    if denominator == 0:
        return MetricValue(None)
    return MetricValue(numerator / denominator, numerator, denominator)


def f1_by_item(judgments: Sequence[CaseJudgment]) -> Mapping[str, ItemF1 | None]:
    """F1 of the ``present`` detection per checklist item; ``None`` when undefined."""
    true_positive: dict[str, int] = {}
    false_positive: dict[str, int] = {}
    false_negative: dict[str, int] = {}
    seen: set[str] = set()
    for judgment in judgments:
        for item_id, gold in judgment.gold.items():
            seen.add(item_id)
            status = judgment.statuses.get(item_id)
            if gold == "present" and status == "present":
                true_positive[item_id] = true_positive.get(item_id, 0) + 1
            elif gold == "present":
                false_negative[item_id] = false_negative.get(item_id, 0) + 1
            elif status == "present":
                false_positive[item_id] = false_positive.get(item_id, 0) + 1

    table: dict[str, ItemF1 | None] = {}
    for item_id in sorted(seen):
        tp = true_positive.get(item_id, 0)
        fp = false_positive.get(item_id, 0)
        fn = false_negative.get(item_id, 0)
        if tp == 0 and fp == 0 and fn == 0:
            table[item_id] = None  # undefined: the item was never really tested
            continue
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        table[item_id] = ItemF1(precision, recall, f1)
    return table


def calibration_error(judgments: Sequence[CaseJudgment]) -> MetricValue:
    """Mean |yes-probability - gold| over the items that carry a probability."""
    numerator = 0.0
    denominator = 0
    for judgment in judgments:
        for item_id, gold in judgment.gold.items():
            probability = judgment.probabilities.get(item_id)
            if probability is None:
                continue
            denominator += 1
            target = 1.0 if gold == "present" else 0.0
            numerator += abs(probability - target)
    if denominator == 0:
        return MetricValue(None)
    return MetricValue(numerator / denominator, numerator=int(numerator), denominator=denominator)


def rule_accuracy(
    cases: Sequence[CaseJudgment],
    fired_by_case: Mapping[str, set[str]],
) -> dict[str, MetricValue]:
    """Exactitud of the code rules M4/M5 against what each case declares as expected."""
    result: dict[str, MetricValue] = {}
    for rule in ("M4", "M5"):
        correct = 0
        for case in cases:
            fired = rule in fired_by_case.get(case.case_id, set())
            if fired == (rule in case.expected_flags):
                correct += 1
        result[rule] = MetricValue(correct / len(cases) if cases else None, correct, len(cases))
    return result


def percentile(values: Sequence[int], quantile: int) -> int | None:
    """Nearest-rank percentile: p95 of a small sample is an observed value, not a blend."""
    if not values:
        return None
    ordered = sorted(values)
    index = -(-quantile * len(ordered) // 100) - 1  # ceil(q * n / 100) - 1
    return ordered[max(0, index)]


def stability(first: Sequence[CaseJudgment], second: Sequence[CaseJudgment]) -> float | None:
    """Agreement between two identical runs, item by item."""
    if len(first) != len(second):
        raise ValueError("stability needs the same cases from both runs")
    same = 0
    total = 0
    for one, other in zip(first, second, strict=True):
        if one.case_id != other.case_id:
            raise ValueError("stability needs the same case order from both runs")
        for item_id, status in one.statuses.items():
            total += 1
            if other.statuses.get(item_id) == status:
                same += 1
    if total == 0:
        return None
    return same / total
