"""ENC-13: the URL mode from the API surface.

The network guard itself is tested in ``test_fetch.py``; here it is only about the contract:
what status a blocked target, an unreadable page and a double input produce, and that the
downloaded text is treated exactly like a pasted one -- including not being stored.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ficha_tecnica.api.app import create_app
from ficha_tecnica.api.fetch import BlockedUrlError, FetchError, FetchTooLargeError

ARTICULO = (
    "SIMULACIÓN. Demoscopia Ficticia S.L. realizó 1.200 entrevistas entre el 3 y el 8 de "
    "noviembre con un margen de error de 2,8 puntos. El Partido Cohete obtendría un 34 %."
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "url.db"


@pytest.fixture
def client(db_path: Path) -> TestClient:
    return TestClient(create_app(db_path=db_path))


def test_a_readable_url_is_analyzed_like_pasted_text(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch(url: str) -> str:
        assert url == "https://ejemplo.test/noticia"
        return ARTICULO

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)

    response = client.post("/v1/analyses", json={"url": "https://ejemplo.test/noticia"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["findings"]) == 15
    assert body["status"] == "ok"


def test_a_blocked_target_answers_400(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str) -> str:
        raise BlockedUrlError("la URL apunta a una red privada o local")

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)

    response = client.post("/v1/analyses", json={"url": "http://192.168.1.1/noticia"})

    assert response.status_code == 400
    assert "red privada" in response.json()["detail"]


def test_an_unreadable_page_answers_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_fetch(url: str) -> str:
        raise FetchError("la pagina respondio 404")

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)

    assert client.post("/v1/analyses", json={"url": "https://ejemplo.test/nada"}).status_code == 502


def test_an_oversized_page_answers_413(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str) -> str:
        raise FetchTooLargeError("la pagina supera el maximo")

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)

    assert (
        client.post("/v1/analyses", json={"url": "https://ejemplo.test/grande"}).status_code == 413
    )


def test_text_and_url_together_are_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/analyses", json={"text": ARTICULO, "url": "https://ejemplo.test/noticia"}
    )

    assert response.status_code == 422


def test_an_empty_page_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_fetch(url: str) -> str:
        return "   "

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)

    assert (
        client.post("/v1/analyses", json={"url": "https://ejemplo.test/vacia"}).status_code == 422
    )


def test_the_downloaded_text_is_not_stored(
    db_path: Path, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same promise as the text mode: the story never reaches the database."""

    async def fake_fetch(url: str) -> str:
        return ARTICULO

    monkeypatch.setattr("ficha_tecnica.api.app.fetch_article", fake_fetch)
    client.post("/v1/analyses", json={"url": "https://ejemplo.test/noticia"})

    connection = sqlite3.connect(db_path)
    try:
        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        dump = " ".join(
            " ".join(str(value) for value in row)
            for table in tables
            for row in connection.execute(f"SELECT * FROM {table}")
        )
        kinds = [row[0] for row in connection.execute("SELECT input_kind FROM analysis")]
    finally:
        connection.close()

    assert "Demoscopia Ficticia" not in dump
    assert "1.200 entrevistas" not in dump
    assert kinds == ["url"]
