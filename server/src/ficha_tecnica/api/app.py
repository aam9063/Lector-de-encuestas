"""FastAPI application: /v1/analyses and utilities (sections 5.2 and 8)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ficha_tecnica.api.pipeline import analyze
from ficha_tecnica.api.store import Database
from ficha_tecnica.clef_client import DecisionProvider, MockProvider, NanProvider
from ficha_tecnica.config import Settings, get_settings
from ficha_tecnica.policy import load_policy, resolve_now, within_window
from ficha_tecnica.schema.checklist import load_checklist
from ficha_tecnica.schema.questionnaire import load_questionnaire
from ficha_tecnica.schema.report import Report

MAX_TEXT_CHARS = 50_000


class AnalysisRequest(BaseModel):
    """Either pasted text or a URL. The URL mode is ENC-13 and answers 501 until then."""

    text: str | None = None
    url: str | None = None


class FeedbackRequest(BaseModel):
    item_id: str = Field(min_length=1)
    verdict: Literal["wrong", "right", "unsure"]


def build_provider(
    settings: Settings | None = None,
) -> tuple[DecisionProvider, httpx.AsyncClient | None, Literal["nan", "mock"]]:
    """Choose the provider once, so the two in-flight slots are process-wide.

    Selecting ``nan`` without a key silently degrades to the mock, and says so through the
    name that ends up in every report, because a sheet built from a flat answer must not be
    mistaken for a real reading.
    """
    resolved = settings or get_settings()
    if resolved.provider == "nan" and resolved.nan_key:
        client = httpx.AsyncClient()
        provider = NanProvider(
            client=client,
            api_key=resolved.nan_key,
            base_url=resolved.nan_base_url,
        )
        return provider, client, "nan"
    return MockProvider(), None, "mock"


def create_app(db_path: Path | None = None) -> FastAPI:
    """Build the app. Tests pass their own database path."""
    settings = get_settings()
    database = Database(db_path or Path(settings.database_path))
    provider, http_client, provider_name = build_provider(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        if http_client is not None:
            await http_client.aclose()

    app = FastAPI(
        title="Ficha Técnica",
        description=(
            "Ficha de lectura para noticias de encuestas electorales: qué información "
            "necesaria aparece y cuál falta. No es asesoramiento jurídico: la valoración "
            "corresponde a la Junta Electoral Central."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )
    app.state.db = database
    app.state.provider = provider
    app.state.provider_name = provider_name

    @app.get("/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "provider": provider_name}

    @app.get("/v1/config")
    def config() -> dict[str, object]:
        policy = load_policy()
        moment = resolve_now(policy.veda)
        return {
            "checklist_version": load_checklist().version,
            "questionnaire_version": load_questionnaire().version,
            "policy_version": policy.version,
            "provider": provider_name,
            "veda": {
                "mode": policy.veda.mode,
                "active": within_window(moment, policy.veda),
                "start": policy.veda.start.isoformat(),
                "end": policy.veda.end.isoformat(),
            },
        }

    @app.get("/v1/checklist")
    def checklist() -> dict[str, object]:
        live = load_checklist()
        return {
            "version": live.version,
            "items": [item.model_dump() for item in live.items],
        }

    @app.post("/v1/analyses", response_model=Report)
    async def create_analysis(request: AnalysisRequest) -> Report:
        if request.url is not None and request.text is None:
            raise HTTPException(
                status_code=501,
                detail="El modo URL llega en ENC-13. Pega el texto de la noticia.",
            )
        text = (request.text or "").strip()
        if not text:
            raise HTTPException(status_code=422, detail="El texto de la noticia está vacío.")
        if len(text) > MAX_TEXT_CHARS:
            raise HTTPException(
                status_code=413,
                detail=f"El texto supera el máximo de {MAX_TEXT_CHARS} caracteres.",
            )

        policy = load_policy()
        calls: list[dict[str, object]] = []
        report = await analyze(
            text,
            provider=provider,
            policy=policy,
            provider_name=provider_name,
            calls=calls,
        )
        await database.save_report(report, calls=calls)
        return report

    @app.get("/v1/analyses/{analysis_id}", response_model=Report)
    async def get_analysis(analysis_id: str) -> Report:
        report = await database.get_report(analysis_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Análisis no encontrado.")
        return report

    @app.post("/v1/analyses/{analysis_id}/feedback")
    async def post_feedback(analysis_id: str, request: FeedbackRequest) -> dict[str, str]:
        if not await database.exists(analysis_id):
            raise HTTPException(status_code=404, detail="Análisis no encontrado.")
        await database.save_feedback(analysis_id, request.item_id, request.verdict)
        return {"status": "ok"}

    return app


app = create_app()
