"""Checklist v1 as typed models (section 6.3 and ``config/checklist.v1.yaml``).

The checklist is data, not code: every item carries its layer (formal or methodological)
and its weight, which is what turns a missing item into a red or amber sheet.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from ficha_tecnica.policy.states import Layer, Weight

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


class ChecklistItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    layer: Layer
    weight: Weight
    base: str
    question: str


class Checklist(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    items: tuple[ChecklistItem, ...]


def load_checklist(path: Path | None = None) -> Checklist:
    """Read the checklist from disk (``config/checklist.v1.yaml`` by default)."""
    source = path or (_CONFIG_DIR / "checklist.v1.yaml")
    with source.open(encoding="utf-8") as stream:
        data: dict[str, object] = yaml.safe_load(stream)
    return Checklist.model_validate(data)
