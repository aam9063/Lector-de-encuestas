"""Typed questionnaire v1 loaded from YAML (ENC-05 T1) and its snapshot (ENC-06)."""

import json
from pathlib import Path
from typing import Any

import pytest

from ficha_tecnica.clef_client.models import ChoiceQuestion, ScoreQuestion
from ficha_tecnica.schema.questionnaire import load_questionnaire

SNAPSHOTS = Path(__file__).parent / "fixtures" / "snapshots"


def _payload(questionnaire: Any) -> dict[str, Any]:
    """Serializable view of the questionnaire: ids next to their Clef question models."""
    return {
        "version": questionnaire.version,
        "groups": {
            name: [{"id": question.id, **question.payload.model_dump()} for question in group]
            for name, group in questionnaire.groups.items()
        },
    }


def test_load_questionnaire_groups_and_counts() -> None:
    questionnaire = load_questionnaire()
    assert questionnaire.version == 1
    assert set(questionnaire.groups) == {"A", "B", "C"}
    assert [len(group) for group in questionnaire.groups.values()] == [15, 6, 2]
    questions = questionnaire.questions()
    assert len(questions) == 23
    assert "a_sample_size" in questions
    assert "b_poll_type" in questions
    assert "c_leading" in questions


def test_choice_criteria_is_a_dict() -> None:
    """The live API rejects anything but an object here (docs/clef-contract.md)."""
    payload = load_questionnaire().questions()["b_poll_type"]
    assert isinstance(payload, ChoiceQuestion)
    assert isinstance(payload.criteria, dict)
    assert payload.criteria["voting_intention_estimate"] == (
        "a model or seat estimate derived from polls"
    )
    assert payload.criteria["not_a_poll"] == "not a survey"


def test_score_criteria_is_an_ordered_list() -> None:
    """The live API rejects anything but an ordered list here (docs/clef-contract.md)."""
    payload = load_questionnaire().questions()["b_headline_overreach"]
    assert isinstance(payload, ScoreQuestion)
    assert payload.criteria == ["Nada", "Poco", "Algo", "Bastante", "Mucho"]


def test_unknown_type_fails_with_a_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "version: 1\n"
        "groups:\n"
        "  A:\n"
        "    - id: a_entity\n"
        "      type: poll\n"
        "      instructions: Does the text say who conducted the poll?\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown type 'poll'"):
        load_questionnaire(path)


def test_question_that_fails_model_validation_reports_the_id(tmp_path: Path) -> None:
    """A choice with list criteria is the exact mistake the live API rejected."""
    path = tmp_path / "bad.yaml"
    path.write_text(
        "version: 1\n"
        "groups:\n"
        "  B:\n"
        "    - id: b_poll_type\n"
        "      type: choice\n"
        "      instructions: What kind of survey?\n"
        "      criteria: [one, two]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="question 'b_poll_type' in group 'B'"):
        load_questionnaire(path)


def test_snapshot_questionnaire() -> None:
    text = json.dumps(_payload(load_questionnaire()), ensure_ascii=False, indent=2) + "\n"
    assert text == (SNAPSHOTS / "questionnaire.v1.json").read_text(encoding="utf-8")
