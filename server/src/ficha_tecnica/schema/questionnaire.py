"""Typed questionnaire v1 loaded from ``config/questionnaire.v1.yaml`` (section 6.3).

Every question in the YAML must produce a valid Clef question model from
``ficha_tecnica.clef_client.models``: catching a bad field name here is cheap,
while in production it would surface as a 400 from the API.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from ficha_tecnica.clef_client.models import (
    ChoiceQuestion,
    NoulQuestion,
    Question,
    ScoreQuestion,
)

_CONFIG_DIR = Path(__file__).resolve().parents[4] / "config"


@dataclass(frozen=True)
class TypedQuestion:
    """One questionnaire item: its checklist id plus the Clef question payload."""

    id: str
    payload: Question


@dataclass(frozen=True)
class Questionnaire:
    """The typed questionnaire: a version and its groups by name."""

    version: int
    groups: dict[str, tuple[TypedQuestion, ...]]

    def questions(self) -> dict[str, Question]:
        """All questions keyed by id, in questionnaire order."""
        return {
            question.id: question.payload for group in self.groups.values() for question in group
        }


def load_questionnaire(path: Path | None = None) -> Questionnaire:
    """Load the questionnaire and validate every question against the Clef models."""
    file = path if path is not None else _CONFIG_DIR / "questionnaire.v1.yaml"
    with file.open(encoding="utf-8") as stream:
        data: dict[str, Any] = yaml.safe_load(stream)
    groups: dict[str, tuple[TypedQuestion, ...]] = {
        name: tuple(_load_question(name, item) for item in items)
        for name, items in data["groups"].items()
    }
    return Questionnaire(version=int(data["version"]), groups=groups)


def _load_question(group: str, item: dict[str, Any]) -> TypedQuestion:
    """Build one typed question, failing loudly on an unknown type or bad fields."""
    question_id = str(item["id"])
    question_type = item.get("type")
    try:
        if question_type == "noul":
            payload: Question = NoulQuestion(instructions=item["instructions"])
        elif question_type == "choice":
            payload = ChoiceQuestion(instructions=item["instructions"], criteria=item["criteria"])
        elif question_type == "score":
            payload = ScoreQuestion(instructions=item["instructions"], criteria=item["criteria"])
        else:
            raise ValueError(
                f"question {question_id!r} in group {group!r} has unknown type {question_type!r}"
            )
    except ValidationError as error:
        raise ValueError(
            f"question {question_id!r} in group {group!r} is not a valid "
            f"{question_type!r} question: {error}"
        ) from error
    return TypedQuestion(id=question_id, payload=payload)
