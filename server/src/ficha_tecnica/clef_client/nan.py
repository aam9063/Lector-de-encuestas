"""Adapter for the real Clef API at NaN (``POST /v1/systemone``, ``model: "clef"``).

NaN allows at most two requests in flight per person. This adapter enforces that with
one semaphore per provider instance, which is the process-wide slot when the app keeps
a single provider. A 429 means a slot was taken elsewhere: it is retried immediately,
never with exponential backoff, because the wait is expected to be microseconds.
"""

import asyncio
import json
from collections.abc import Mapping

import httpx

from ficha_tecnica.clef_client.errors import (
    ClefAuthError,
    ClefBadRequestError,
    ClefError,
    ClefTimeoutError,
    ClefUnavailableError,
)
from ficha_tecnica.clef_client.models import ClefResponse, Question

DEFAULT_BASE_URL = "https://api.nan.builders"
SYSTEMONE_PATH = "/v1/systemone"
MODEL = "clef"


def _api_message(response: httpx.Response) -> str:
    """The API documents ``{"error": {"message": ...}}``; fall back to raw text."""
    try:
        payload = response.json()
    except json.JSONDecodeError, ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return f"HTTP {response.status_code}"


class NanProvider:
    """``DecisionProvider`` backed by the live NaN API."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 10.0,
        max_attempts: int = 5,
        retry_delay: float = 0.2,
        max_in_flight: int = 2,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._url = f"{base_url.rstrip('/')}{SYSTEMONE_PATH}"
        self._timeout = timeout
        self._max_attempts = max_attempts
        self._retry_delay = retry_delay
        self._slots = asyncio.Semaphore(max_in_flight)

    async def ask(self, state: str, questions: Mapping[str, Question]) -> ClefResponse:
        body = {
            "model": MODEL,
            "state": state,
            "questions": {
                question_id: question.model_dump() for question_id, question in questions.items()
            },
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        async with self._slots:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = await self._client.post(
                        self._url, json=body, headers=headers, timeout=self._timeout
                    )
                except httpx.TimeoutException as error:
                    raise ClefTimeoutError(
                        f"Clef did not answer within {self._timeout}s"
                    ) from error
                except httpx.HTTPError as error:
                    raise ClefError(f"Clef transport error: {error}") from error

                if response.status_code == 429:
                    if attempt == self._max_attempts:
                        raise ClefUnavailableError(
                            f"Clef returned 429 on all {self._max_attempts} attempts: "
                            "the two-in-flight limit is saturated"
                        )
                    await asyncio.sleep(self._retry_delay)
                    continue

                if response.status_code in {401, 403}:
                    raise ClefAuthError(_api_message(response))
                if response.status_code in {400, 413}:
                    raise ClefBadRequestError(_api_message(response))
                if response.status_code >= 500:
                    raise ClefUnavailableError(_api_message(response))

                response.raise_for_status()
                return ClefResponse.model_validate(response.json())

        raise ClefUnavailableError("Clef: exhausted the attempt budget")  # pragma: no cover
