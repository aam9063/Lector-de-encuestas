"""Response models must parse the three real Clef answer shapes (docs/clef-contract.md)."""

import json
from pathlib import Path

import pytest

from ficha_tecnica.clef_client.models import (
    ChoiceAnswer,
    ClefResponse,
    NoulAnswer,
    ScoreAnswer,
)

FIXTURES = Path(__file__).parent / "fixtures" / "clef"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parse_noul_answer_from_real_fixture() -> None:
    response = ClefResponse.model_validate(_load("smoke_real.json"))

    assert response.object == "structured_decision"
    assert response.model == "clef"
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens == 0

    answer = response.answers["a_sample_size"]
    assert isinstance(answer, NoulAnswer)
    assert answer.type == "noul"
    assert 0.0 <= answer.noul <= 1.0
    assert answer.probabilities["yes"] == pytest.approx(answer.noul)
    assert sum(answer.probabilities.values()) == pytest.approx(1.0)
    assert answer.confidence == pytest.approx(answer.noul)


def test_parse_choice_answer_from_real_fixture() -> None:
    response = ClefResponse.model_validate(_load("smoke_choice.json"))

    answer = response.answers["b_poll_type"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.type == "choice"
    assert answer.choice in answer.probabilities
    assert sum(answer.probabilities.values()) == pytest.approx(1.0)
    assert answer.probabilities[answer.choice] == pytest.approx(answer.confidence)


def test_parse_score_answer_from_real_fixture() -> None:
    response = ClefResponse.model_validate(_load("smoke_score.json"))

    answer = response.answers["b_headline_overreach"]
    assert isinstance(answer, ScoreAnswer)
    assert answer.type == "score"
    # A continuous position on the ordered levels, 0..len(levels)-1.
    assert 0.0 <= answer.score <= 4.0
    assert answer.legend["0"] == "Nada"
    assert answer.legend["4"] == "Mucho"
    assert len(answer.probabilities) == 5
    assert sum(answer.probabilities.values()) == pytest.approx(1.0)


def test_probability_of_yes_is_exposed_uniformly() -> None:
    """The policy should not care which answer type produced a probability."""
    response = ClefResponse.model_validate(_load("smoke_real.json"))

    assert response.answers["a_sample_size"].yes_probability() == pytest.approx(0.9867772459983826)


def test_unknown_fields_do_not_break_parsing() -> None:
    payload = _load("smoke_real.json")
    payload["unexpected_future_field"] = {"anything": True}
    payload["answers"]["a_sample_size"]["another_new_field"] = 1

    response = ClefResponse.model_validate(payload)

    assert isinstance(response.answers["a_sample_size"], NoulAnswer)


def test_answer_type_discriminates_on_the_type_field() -> None:
    payload = _load("smoke_real.json")
    payload["answers"]["a_sample_size"]["type"] = "not_a_known_type"

    with pytest.raises(ValueError):
        ClefResponse.model_validate(payload)
