"""Settings must accept the API key under either documented env var name."""

import pytest
from pydantic import ValidationError

from ficha_tecnica.config import Settings


@pytest.mark.parametrize("var_name", ["NAN_KEY", "NAN_API_KEY"])
def test_api_key_read_from_either_env_var(monkeypatch: pytest.MonkeyPatch, var_name: str) -> None:
    monkeypatch.delenv("NAN_KEY", raising=False)
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    monkeypatch.setenv(var_name, "clave-de-prueba")

    settings = Settings()

    assert settings.nan_key == "clave-de-prueba"


@pytest.mark.parametrize("var_name", ["CLEF_PROVIDER", "PROVIDER"])
def test_provider_read_from_either_env_var(monkeypatch: pytest.MonkeyPatch, var_name: str) -> None:
    monkeypatch.delenv("CLEF_PROVIDER", raising=False)
    monkeypatch.delenv("PROVIDER", raising=False)
    monkeypatch.setenv(var_name, "nan")

    settings = Settings()

    assert settings.provider == "nan"


def test_provider_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLEF_PROVIDER", raising=False)
    monkeypatch.delenv("PROVIDER", raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]  # ignore any local .env

    assert settings.provider == "mock"


def test_provider_rejects_unknown_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEF_PROVIDER", "otro")

    with pytest.raises(ValidationError):
        Settings()
