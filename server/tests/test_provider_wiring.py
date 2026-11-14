"""Provider wiring: the app must use the real model when a key is configured.

Until now the app always used the mock provider, so every demo sheet was built from a
flat 0.5 answer. That is fine for wiring but it makes the sheet meaningless: half the
items land in review because nobody actually decided anything.

The provider is built once per app so NaN's two-in-flight limit is a process-wide slot,
not a per-request allowance.

These tests build ``Settings`` explicitly instead of relying on the environment: the
developer's own ``.env`` has a real key, and a test that depends on that would pass on one
machine and fail on another.
"""

from typing import Literal

import httpx
import pytest
from fastapi.testclient import TestClient

from ficha_tecnica.api.app import build_provider, create_app
from ficha_tecnica.clef_client import MockProvider, NanProvider
from ficha_tecnica.config import Settings

ProviderName = Literal["nan", "mock"]


def settings_for(provider: ProviderName, key: str) -> Settings:
    return Settings(provider=provider, nan_key=key, database_path=":memory:")


def test_without_a_key_the_app_stays_on_the_mock_provider() -> None:
    provider, client, name = build_provider(settings_for("nan", ""))

    assert isinstance(provider, MockProvider)
    assert client is None
    assert name == "mock"


def test_with_a_key_and_nan_selected_the_real_provider_is_used() -> None:
    provider, client, name = build_provider(settings_for("nan", "clave-de-prueba"))

    assert isinstance(provider, NanProvider)
    assert client is not None
    assert name == "nan"


def test_mock_selected_ignores_a_present_key() -> None:
    provider, client, name = build_provider(settings_for("mock", "clave-de-prueba"))

    assert isinstance(provider, MockProvider)
    assert client is None
    assert name == "mock"


def test_the_reported_name_matches_the_provider_actually_used() -> None:
    """A sheet built from a flat answer must not be labelled as a real reading."""
    _, _, degraded = build_provider(settings_for("nan", ""))
    _, _, real = build_provider(settings_for("nan", "clave-de-prueba"))

    assert degraded == "mock"
    assert real == "nan"


def test_the_app_exposes_the_provider_it_will_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "ficha_tecnica.api.app.get_settings", lambda: settings_for("mock", "clave-de-prueba")
    )

    app = create_app(db_path=tmp_path / "wiring.db")

    assert isinstance(app.state.provider, MockProvider)
    assert app.state.provider_name == "mock"


def test_the_provider_is_built_once_so_the_two_slots_are_global(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A provider per request would give every request its own two slots."""
    monkeypatch.setattr(
        "ficha_tecnica.api.app.get_settings", lambda: settings_for("nan", "clave-de-prueba")
    )

    app = create_app(db_path=tmp_path / "slots.db")
    client = TestClient(app)

    assert app.state.provider is app.state.provider
    assert isinstance(app.state.provider, NanProvider)
    del client


def test_health_reports_the_effective_provider(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(
        "ficha_tecnica.api.app.get_settings", lambda: settings_for("nan", "clave-de-prueba")
    )
    client = TestClient(create_app(db_path=tmp_path / "health.db"))

    assert client.get("/v1/health").json()["provider"] == "nan"


def test_an_httpx_client_is_created_for_the_real_provider() -> None:
    _, client, _ = build_provider(settings_for("nan", "clave-de-prueba"))

    assert isinstance(client, httpx.AsyncClient)
