"""Report models (section 8). Pydantic is the source of truth; the web generates its
types from the OpenAPI schema.

There is deliberately no field that could hold the news text: only ``text_hash``. A field
that does not exist cannot be filled by accident, and a test asserts the absence.
"""

from typing import Literal

from pydantic import BaseModel, Field

ItemStatus = Literal["present", "absent", "refers_external", "review"]
Layer = Literal["formal", "methodological", "auxiliary"]
Severity = Literal["high", "medium", "low", "note"]
Source = Literal["code", "clef", "both", "computation"]
Semaphore = Literal["red", "amber", "green", "grey"]


class Span(BaseModel):
    """A range on the text the user pasted, so a client can highlight it."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class Finding(BaseModel):
    """One checklist item's outcome. The message is a fixed template: no figures, no names."""

    item_id: str
    layer: Layer
    status: ItemStatus
    severity: Severity
    source: Source
    probability: float | None = None
    evidence: list[Span] = []
    message: str


class Computation(BaseModel):
    """The arithmetic behind M4 and M5, expressed as figures and ratios, never as a party."""

    sample_size: int | None = None
    declared_margin: float | None = None
    theoretical_margin: float | None = None
    lead_ratio: float | None = None


class Report(BaseModel):
    """A reading sheet. Describes the information the news gives, never the poll's quality."""

    id: str
    created_at: str
    text_hash: str
    checklist_version: int
    questionnaire_version: int
    provider: Literal["nan", "mock"]
    poll_type: str
    poll_type_probs: dict[str, float] = {}
    semaphore: Semaphore
    status: Literal["ok", "veda"]
    findings: list[Finding]
    computation: Computation | None = None
    disclaimer: str
    latency_ms: int
