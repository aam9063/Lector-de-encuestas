"""Settings must accept the API key under either documented env var name."""

import pytest

from ficha_tecnica.config import Settings


@pytest.mark.parametrize("var_name", ["NAN_KEY", "NAN_API_KEY"])
def test_api_key_read_from_either_env_var(monkeypatch: pytest.MonkeyPatch, var_name: str) -> None:
    monkeypatch.delenv("NAN_KEY", raising=False)
    monkeypatch.delenv("NAN_API_KEY", raising=False)
    monkeypatch.setenv(var_name, "clave-de-prueba")

    settings = Settings()

    assert settings.nan_key == "clave-de-prueba"
