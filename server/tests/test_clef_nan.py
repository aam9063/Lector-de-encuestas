"""NanProvider: request shape, the 2-in-flight semaphore and the error mapping."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from ficha_tecnica.clef_client import (
    ChoiceQuestion,
    ClefAuthError,
    ClefBadRequestError,
    ClefTimeoutError,
    ClefUnavailableError,
    NanProvider,
    NoulQuestion,
    ScoreQuestion,
)

FIXTURES = Path(__file__).parent / "fixtures" / "clef"
NOUL_FIXTURE = json.loads((FIXTURES / "smoke_real.json").read_text(encoding="utf-8"))

STATE = "SIMULACION. Encuesta de Demoscopia Ficticia con 1.200 entrevistas."
QUESTIONS = {
    "a_sample_size": NoulQuestion(instructions="How many people were interviewed?"),
    "b_poll_type": ChoiceQuestion(
        instructions="What kind of survey?",
        criteria={"voting_intention_estimate": "seats model", "not_a_poll": "not a poll"},
    ),
    "b_headline_overreach": ScoreQuestion(
        instructions="How much does the headline overreach?",
        criteria=["Nada", "Poco", "Mucho"],
    ),
}


def _provider(handler, **kwargs) -> NanProvider:
    return NanProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        api_key="clave-de-prueba",
        retry_delay=0.0,
        **kwargs,
    )


async def test_sends_the_documented_request() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=NOUL_FIXTURE)

    provider = _provider(handler)
    await provider.ask(STATE, QUESTIONS)

    assert captured["url"] == "https://api.nan.builders/v1/systemone"
    assert captured["auth"] == "Bearer clave-de-prueba"
    assert captured["body"]["model"] == "clef"
    assert captured["body"]["state"] == STATE
    assert captured["body"]["questions"]["a_sample_size"] == {
        "type": "noul",
        "instructions": "How many people were interviewed?",
    }
    assert captured["body"]["questions"]["b_poll_type"]["criteria"] == {
        "voting_intention_estimate": "seats model",
        "not_a_poll": "not a poll",
    }
    assert captured["body"]["questions"]["b_headline_overreach"]["criteria"] == [
        "Nada",
        "Poco",
        "Mucho",
    ]


async def test_retries_immediately_on_429() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"message": "too many"}})
        return httpx.Response(200, json=NOUL_FIXTURE)

    provider = _provider(handler)
    response = await provider.ask(STATE, QUESTIONS)

    assert len(calls) == 2
    assert response.answers["a_sample_size"].type == "noul"


async def test_gives_up_after_the_last_attempt_on_sustained_429() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(429, json={"error": {"message": "too many"}})

    provider = _provider(handler, max_attempts=5)

    with pytest.raises(ClefUnavailableError):
        await provider.ask(STATE, QUESTIONS)

    assert len(calls) == 5


async def test_401_raises_auth_error_without_retrying() -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": {"message": "invalid key"}})

    provider = _provider(handler)

    with pytest.raises(ClefAuthError):
        await provider.ask(STATE, QUESTIONS)

    assert len(calls) == 1


@pytest.mark.parametrize("status", [400, 413])
async def test_bad_request_surfaces_the_api_message(status: int) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            json={"error": {"message": "score criteria must be an ordered list"}},
        )

    provider = _provider(handler)

    with pytest.raises(ClefBadRequestError, match="ordered list"):
        await provider.ask(STATE, QUESTIONS)


async def test_timeout_raises_a_timeout_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    provider = _provider(handler)

    with pytest.raises(ClefTimeoutError):
        await provider.ask(STATE, QUESTIONS)


async def test_never_exceeds_two_requests_in_flight() -> None:
    in_flight = 0
    peak = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return httpx.Response(200, json=NOUL_FIXTURE)

    provider = _provider(handler)
    await asyncio.gather(*(provider.ask(STATE, QUESTIONS) for _ in range(6)))

    assert peak == 2
