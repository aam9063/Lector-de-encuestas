"""Smoke tests for the scaffolded application."""

import fastapi
import pydantic
import pytest
from fastapi.testclient import TestClient

from ficha_tecnica import __version__
from ficha_tecnica.api.app import app
from ficha_tecnica.config import Settings


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_settings_do_not_require_nan_key() -> None:
    settings = Settings()
    assert settings.provider in {"mock", "nan"}
    assert settings.nan_base_url.startswith("https://")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_stack_versions() -> None:
    assert fastapi.__version__ >= "0.118"
    assert pydantic.VERSION >= "2.12"
