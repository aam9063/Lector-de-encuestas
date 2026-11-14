"""ENC-18: several users at once, and the two slots NaN gives us.

NaN allows two requests in flight per person. That is a process-wide budget, so the thing
worth testing is not one request: it is what happens when eight people press "analizar" at
the same time and each analysis needs two or three calls.

A per-request semaphore would look correct in a single-call test and still blow past the
limit in the wild, which is why the provider is built once per app and these tests share a
single instance.
"""

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.clef_client import NanProvider
from ficha_tecnica.policy import load_policy

FIXTURES = Path(__file__).parent / "fixtures" / "clef"
NOUL = json.loads((FIXTURES / "smoke_real.json").read_text(encoding="utf-8"))

NEWS = (
    "SIMULACIÓN. Demoscopia Ficticia S.L. realizó 1.200 entrevistas entre el 3 y el 8 de "
    "noviembre con un margen de error de 2,8 puntos. El Partido Cohete obtendría un 34 %."
)

USERS = 8


class Transport:
    """A fake API that counts how many requests are open at the same time."""

    def __init__(self, *, answer_429_first: int = 0) -> None:
        self.in_flight = 0
        self.peak = 0
        self.calls = 0
        self.delays: dict[int, int] = {}
        self._answer_429_first = answer_429_first
        self._attempts = 0

    async def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        self._attempts += 1
        if self._attempts <= self._answer_429_first:
            return httpx.Response(429, json={"error": {"message": "too many"}})

        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(0.01)
        finally:
            self.in_flight -= 1
        return httpx.Response(200, json=NOUL)


def provider_for(transport: Transport) -> NanProvider:
    return NanProvider(
        client=httpx.AsyncClient(transport=httpx.MockTransport(transport.handler)),
        api_key="clave-de-prueba",
        retry_delay=0.0,
    )


async def test_eight_users_at_once_never_exceed_the_two_slots() -> None:
    transport = Transport()
    provider = provider_for(transport)

    reports = await asyncio.gather(
        *(analyze(NEWS, provider=provider, policy=load_policy()) for _ in range(USERS))
    )

    assert len(reports) == USERS
    assert all(report.findings for report in reports)
    assert transport.peak == 2, f"se abrieron {transport.peak} peticiones a la vez"


async def test_every_user_gets_an_answer_even_when_the_queue_is_saturated() -> None:
    """Serialising is the point: it must slow down, not fail."""
    transport = Transport()
    provider = provider_for(transport)

    reports = await asyncio.gather(
        *(analyze(NEWS, provider=provider, policy=load_policy()) for _ in range(USERS))
    )

    assert all(len(report.findings) == 15 for report in reports)
    assert transport.calls >= USERS


async def test_a_429_wave_is_retried_and_no_user_loses_their_sheet() -> None:
    transport = Transport(answer_429_first=4)
    provider = provider_for(transport)

    reports = await asyncio.gather(
        *(analyze(NEWS, provider=provider, policy=load_policy()) for _ in range(4))
    )

    assert all(len(report.findings) == 15 for report in reports)
    assert transport.calls > 4


async def test_the_budget_is_shared_by_the_whole_app_and_not_per_request() -> None:
    """Two providers would each own two slots and the process would use four."""
    transport = Transport()
    provider = provider_for(transport)

    await asyncio.gather(
        *(analyze(NEWS, provider=provider, policy=load_policy()) for _ in range(USERS))
    )

    assert transport.peak <= 2


@pytest.mark.parametrize("users", [1, 3])
async def test_the_limit_holds_for_small_numbers_too(users: int) -> None:
    transport = Transport()
    provider = provider_for(transport)

    await asyncio.gather(
        *(analyze(NEWS, provider=provider, policy=load_policy()) for _ in range(users))
    )

    assert transport.peak <= 2
