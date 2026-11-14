"""FastAPI application: /v1/analyses and utilities (sections 8 and 5.2)."""

from fastapi import FastAPI

from ficha_tecnica.config import get_settings

app = FastAPI(
    title="Ficha Técnica",
    description=(
        "Ficha de lectura para noticias de encuestas electorales: qué información "
        "necesaria aparece y cuál falta. No es asesoramiento jurídico: la valoración "
        "corresponde a la Junta Electoral Central."
    ),
    version="0.1.0",
)


@app.get("/v1/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "provider": settings.provider,
        "checklist_version": str(settings.checklist_version),
        "questionnaire_version": str(settings.questionnaire_version),
    }
