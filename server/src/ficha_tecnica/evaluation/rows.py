"""Row and report types shared by the runner and the renderers.

They live apart so ``render`` can consume a report without importing the runner
(and without a circular import): the runner builds reports, the renderers draw them.
"""

from dataclasses import dataclass

from ficha_tecnica.evaluation.metrics import ItemF1, MetricValue


@dataclass(frozen=True)
class BaselineRow:
    """One table row: the metrics of one baseline, or its unavailability."""

    baseline: str
    false_accusation: MetricValue
    omission_recall: MetricValue
    review_fraction: MetricValue
    ece: MetricValue
    case_count: int
    m4: MetricValue | None = None
    m5: MetricValue | None = None
    stability: MetricValue | None = None
    latency_p50_ms: int | None = None
    latency_p95_ms: int | None = None
    f1: dict[str, ItemF1 | None] | None = None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class HarnessReport:
    """Everything the CLI prints: rows, notes, leak counter and the rendered outputs."""

    provider_name: str
    rows: tuple[BaselineRow, ...]
    cases_considered: int
    leak_count: int
    notes: tuple[str, ...] = ()
    table: str = ""
    chart: str = ""
