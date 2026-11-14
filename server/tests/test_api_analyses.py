"""ENC-11: the /v1/analyses API and the promise that the news text is never stored.

The most important test in this file is the one that reads the SQLite file directly and
looks for the pasted text in every column: a promise about not storing something has to be
checked against the storage, not against the code's intentions.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ficha_tecnica.api.app import create_app

NEWS = (
    "SIMULACION. El Partido Popular ganaria las elecciones segun una encuesta de "
    "Demoscopia Ficticia S.L. El estudio se hizo con 1.200 entrevistas entre el 3 y el 9 "
    "de noviembre. El margen de error es de 2,8 puntos. El Partido Popular obtendria un "
    "32 % de los votos y el PSOE un 28 %."
)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "ficha.db"


@pytest.fixture
def client(db_path: Path) -> TestClient:
    return TestClient(create_app(db_path=db_path))


@pytest.fixture
def created(client: TestClient) -> dict:
    response = client.post("/v1/analyses", json={"text": NEWS})
    assert response.status_code == 200, response.text
    return response.json()


def test_analyzing_text_returns_a_sheet(client: TestClient, created: dict) -> None:
    assert created["id"]
    assert created["semaphore"] in {"red", "amber", "green", "grey"}
    assert len(created["findings"]) == 15


def test_the_response_is_already_sanitized(created: dict) -> None:
    from ficha_tecnica.sanitizer import find_leaks

    serialized = json.dumps(created, ensure_ascii=False)

    assert find_leaks(serialized) == []
    assert "32 %" not in serialized


def test_a_sheet_can_be_retrieved_by_id(client: TestClient, created: dict) -> None:
    response = client.get(f"/v1/analyses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_an_unknown_id_is_404(client: TestClient) -> None:
    assert client.get("/v1/analyses/no-existe").status_code == 404


def test_feedback_is_accepted(client: TestClient, created: dict) -> None:
    response = client.post(
        f"/v1/analyses/{created['id']}/feedback",
        json={"item_id": "a_sample_size", "verdict": "wrong"},
    )

    assert response.status_code == 200


def test_feedback_for_an_unknown_analysis_is_404(client: TestClient) -> None:
    response = client.post(
        "/v1/analyses/no-existe/feedback",
        json={"item_id": "a_sample_size", "verdict": "wrong"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("payload", [{}, {"text": "   "}, {"text": ""}])
def test_an_empty_text_is_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/v1/analyses", json=payload).status_code == 422


def test_an_oversized_text_is_rejected(client: TestClient) -> None:
    response = client.post("/v1/analyses", json={"text": "a" * 60_000})

    assert response.status_code == 413


def test_config_reports_versions_and_the_blackout(client: TestClient) -> None:
    body = client.get("/v1/config").json()

    assert body["checklist_version"] == 1
    assert body["questionnaire_version"] == 1
    assert body["policy_version"] == 1
    assert body["veda"]["mode"] in {"strict", "off"}


def test_the_checklist_endpoint_lists_every_item(client: TestClient) -> None:
    body = client.get("/v1/checklist").json()

    assert len(body["items"]) == 15
    assert {item["layer"] for item in body["items"]} <= {
        "formal",
        "methodological",
        "auxiliary",
    }


def test_the_news_text_is_never_written_to_the_database(db_path: Path, client: TestClient) -> None:
    """Read the raw file: every row of every table, every column, as text."""
    client.post("/v1/analyses", json={"text": NEWS})

    connection = sqlite3.connect(db_path)
    try:
        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        dump = []
        for table in tables:
            for row in connection.execute(f"SELECT * FROM {table}"):
                dump.append(" ".join(str(value) for value in row))
        contents = "\n".join(dump)
    finally:
        connection.close()

    assert tables, "the database should have tables"
    for fragment in ("Demoscopia Ficticia", "1.200 entrevistas", "32 %", "Partido Popular"):
        assert fragment not in contents, f"the database stored {fragment!r}"
    assert NEWS[:60] not in contents


def test_the_database_keeps_a_hash_instead(db_path: Path, client: TestClient) -> None:
    created = client.post("/v1/analyses", json={"text": NEWS}).json()

    connection = sqlite3.connect(db_path)
    try:
        stored = connection.execute("SELECT text_hash FROM analysis").fetchone()[0]
    finally:
        connection.close()

    assert stored == created["text_hash"]
    assert len(stored) == 64


def test_the_stored_clef_answers_hold_probabilities_only(db_path: Path, client: TestClient) -> None:
    client.post("/v1/analyses", json={"text": NEWS})

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT raw_answers_json FROM clef_call").fetchall()
    finally:
        connection.close()

    assert rows, "clef calls should be recorded"
    for (raw,) in rows:
        parsed = json.loads(raw)
        assert "state" not in parsed
        assert "digest" not in json.dumps(parsed).lower()
