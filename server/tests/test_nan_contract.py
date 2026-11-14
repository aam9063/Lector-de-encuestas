"""ENC-18: the adapter against the real responses we captured from the API.

The unit tests in `test_clef_nan.py` use hand-built payloads. These replay the bytes the
live API actually returned, so the adapter and the parser cannot drift away from the
contract documented in `docs/clef-contract.md` without a test noticing.
"""

import json
from pathlib import Path

import httpx
import pytest

from ficha_tecnica.clef_client import (
    ChoiceAnswer,
    NanProvider,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
)
from ficha_tecnica.clef_client.models import ChoiceQuestion, ScoreQuestion

FIXTURES = Path(__file__).parent / "fixtures" / "clef"
CAPTURED = {
    "noul": "smoke_real.json",
    "choice": "smoke_choice.json",
    "score": "smoke_score.json",
}


def captured(kind: str) -> dict:
    return json.loads((FIXTURES / CAPTURED[kind]).read_text(encoding="utf-8"))


def provider_answering(payload: dict, seen: list[httpx.Request] | None = None) -> NanProvider:
    async def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return httpx.Response(200, json=payload)

    return NanProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        api_key="clave-de-prueba",
        retry_delay=0.0,
    )


async def test_the_captured_noul_response_parses_through_the_adapter() -> None:
    payload = captured("noul")
    provider = provider_answering(payload)

    response = await provider.ask(
        "SIMULACION. Encuesta con 1.200 entrevistas.",
        {"a_sample_size": NoulQuestion(instructions="How many people were interviewed?")},
    )

    assert response.id == payload["id"]
    assert response.usage.input_tokens == payload["usage"]["input_tokens"]
    answer = response.answers["a_sample_size"]
    assert isinstance(answer, NoulAnswer)
    assert answer.noul == pytest.approx(payload["answers"]["a_sample_size"]["noul"])
    assert answer.yes_probability() == pytest.approx(payload["answers"]["a_sample_size"]["noul"])


async def test_the_captured_choice_response_parses_through_the_adapter() -> None:
    payload = captured("choice")
    provider = provider_answering(payload)

    response = await provider.ask(
        "SIMULACION. Encuesta de intencion de voto.",
        {
            "b_poll_type": ChoiceQuestion(
                instructions="What kind of survey?",
                criteria={"voting_intention_estimate": "seats model", "not_a_poll": "not a poll"},
            )
        },
    )

    answer = response.answers["b_poll_type"]
    assert isinstance(answer, ChoiceAnswer)
    assert answer.choice in answer.probabilities


async def test_the_captured_score_response_parses_through_the_adapter() -> None:
    payload = captured("score")
    provider = provider_answering(payload)

    response = await provider.ask(
        "SIMULACION. El Partido Azul gana claramente.",
        {
            "b_headline_overreach": ScoreQuestion(
                instructions="How much does the headline overreach?",
                criteria=["Nada", "Poco", "Algo", "Bastante", "Mucho"],
            )
        },
    )

    answer = response.answers["b_headline_overreach"]
    assert isinstance(answer, ScoreAnswer)
    assert answer.legend["0"] == "Nada"
    assert set(answer.probabilities) == set(answer.legend)


async def test_the_request_matches_the_documented_contract() -> None:
    """Everything the API accepted once, in the shape it accepted it."""
    seen: list[httpx.Request] = []
    provider = provider_answering(captured("noul"), seen)

    await provider.ask(
        "estado de prueba",
        {
            "a_sample_size": NoulQuestion(instructions="Q1"),
            "b_poll_type": ChoiceQuestion(instructions="Q2", criteria={"x": "d1", "y": "d2"}),
            "b_headline_overreach": ScoreQuestion(instructions="Q3", criteria=["Nada", "Mucho"]),
        },
    )

    request = seen[0]
    assert request.url.path == "/v1/systemone"
    assert request.headers["authorization"] == "Bearer clave-de-prueba"
    body = json.loads(request.content)
    assert body["model"] == "clef"
    assert body["state"] == "estado de prueba"
    # choice takes criteria as an object of label -> description.
    assert body["questions"]["b_poll_type"]["criteria"] == {"x": "d1", "y": "d2"}
    # score takes criteria as an ordered list of levels.
    assert body["questions"]["b_headline_overreach"]["criteria"] == ["Nada", "Mucho"]
    # noul takes no criteria at all.
    assert "criteria" not in body["questions"]["a_sample_size"]


async def test_an_unknown_answer_type_is_a_clear_error_not_a_silent_default() -> None:
    payload = captured("noul")
    payload["answers"]["a_sample_size"]["type"] = "desconocido"
    provider = provider_answering(payload)

    with pytest.raises(ValueError):
        await provider.ask("estado", {"a_sample_size": NoulQuestion(instructions="How many?")})
