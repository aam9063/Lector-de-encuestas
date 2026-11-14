"""SQLite persistence that never keeps the news text (section 9).

The system stores a hash of the input, the configuration used and the results. It does not
store the story: the database is checked directly by a test that dumps every row of every
table and looks for fragments of the pasted text.

Blocking SQLite calls are pushed to a worker thread so a slow disk never stalls the event
loop that is waiting on Clef.
"""

import asyncio
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from ficha_tecnica.schema.report import Report

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    input_kind TEXT NOT NULL,
    checklist_version INTEGER NOT NULL,
    questionnaire_version INTEGER NOT NULL,
    provider TEXT NOT NULL,
    poll_type TEXT NOT NULL,
    semaphore TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    report_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS finding (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES analysis(id),
    item_id TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    probability REAL
);
CREATE TABLE IF NOT EXISTS clef_call (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES analysis(id),
    group_name TEXT NOT NULL,
    model TEXT NOT NULL,
    tokens_in INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    raw_answers_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id TEXT NOT NULL REFERENCES analysis(id),
    item_id TEXT NOT NULL,
    verdict TEXT NOT NULL
);
"""


class Database:
    """Thin async wrapper over SQLite. No method accepts the news text."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    async def save_report(
        self,
        report: Report,
        *,
        input_kind: str = "text",
        calls: Iterable[dict[str, object]] = (),
    ) -> None:
        await asyncio.to_thread(self._save_report, report, input_kind, list(calls))

    def _save_report(self, report: Report, input_kind: str, calls: list[dict[str, object]]) -> None:
        payload = report.model_dump_json()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO analysis (id, created_at, text_hash, input_kind, checklist_version,"
                " questionnaire_version, provider, poll_type, semaphore, status, latency_ms,"
                " report_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    report.id,
                    report.created_at,
                    report.text_hash,
                    input_kind,
                    report.checklist_version,
                    report.questionnaire_version,
                    report.provider,
                    report.poll_type,
                    report.semaphore,
                    report.status,
                    report.latency_ms,
                    payload,
                ),
            )
            connection.executemany(
                "INSERT INTO finding (analysis_id, item_id, status, severity, source, probability)"
                " VALUES (?,?,?,?,?,?)",
                [
                    (
                        report.id,
                        finding.item_id,
                        finding.status,
                        finding.severity,
                        finding.source,
                        finding.probability,
                    )
                    for finding in report.findings
                ],
            )
            connection.executemany(
                "INSERT INTO clef_call (analysis_id, group_name, model, tokens_in, latency_ms,"
                " raw_answers_json) VALUES (?,?,?,?,?,?)",
                [
                    (
                        report.id,
                        str(call.get("group_name", "")),
                        str(call.get("model", "clef")),
                        int(call.get("tokens_in", 0)),  # type: ignore[arg-type]
                        int(call.get("latency_ms", 0)),  # type: ignore[arg-type]
                        json.dumps(call.get("raw_answers", {}), ensure_ascii=False),
                    )
                    for call in calls
                ],
            )

    async def get_report(self, analysis_id: str) -> Report | None:
        return await asyncio.to_thread(self._get_report, analysis_id)

    def _get_report(self, analysis_id: str) -> Report | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM analysis WHERE id = ?", (analysis_id,)
            ).fetchone()
        if row is None:
            return None
        return Report.model_validate_json(row[0])

    async def exists(self, analysis_id: str) -> bool:
        return await asyncio.to_thread(self._exists, analysis_id)

    def _exists(self, analysis_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM analysis WHERE id = ?", (analysis_id,)
            ).fetchone()
        return row is not None

    async def save_feedback(self, analysis_id: str, item_id: str, verdict: str) -> None:
        await asyncio.to_thread(self._save_feedback, analysis_id, item_id, verdict)

    def _save_feedback(self, analysis_id: str, item_id: str, verdict: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback (analysis_id, item_id, verdict) VALUES (?,?,?)",
                (analysis_id, item_id, verdict),
            )
