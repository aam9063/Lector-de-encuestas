# Ficha Técnica

Una app que lee una noticia sobre una encuesta electoral y dice, ítem por ítem, qué
información necesaria para interpretarla aparece y cuál falta. Clef decide qué hay en el
texto; el código comprueba la aritmética y las reglas. Nunca juzga si el resultado es
verdadero ni a favor de quién.

Proyecto del hackathon #2 NaN "Decide con Clef". La ficha técnica completa está en
[`lector-de-encuestas.md`](./lector-de-encuestas.md).

## Stack

- **Backend:** Python 3.14, uv, FastAPI, Pydantic v2 (`server/`)
- **Web:** React 19, TSX, Tailwind CSS v4, Vite (`web/`)
- **Decisiones:** Clef vía API de NaN (`POST /v1/systemone`, `model: "clef"`)

## Estructura

```
server/    API de análisis (FastAPI) y lógica determinista
web/       Interfaz: pegar texto, ficha con semáforo, evidencia
config/    Checklist, cuestionario, política, listas curadas (YAML)
eval/      Dataset sintético con mutaciones, baselines y métricas
odd/tasks/ Documentos de feature (ODD)
docs/      Documentación adicional
```

## Requisitos

- Python 3.14 y [uv](https://docs.astral.sh/uv/)
- Node 22+ y [pnpm](https://pnpm.io/)

## Arranque

```bash
# 1. Variables de entorno: crea .env en la raíz con tu clave de NaN
echo 'NAN_KEY=tu-clave' > .env

# 2. Backend
cd server && uv sync && uv run pytest
uv run uvicorn ficha_tecnica.api.app:app --reload --env-file ../.env

# 3. Web (otra terminal)
pnpm --dir web install && pnpm --dir web dev
```

La web hace proxy de `/v1` hacia `http://localhost:8000`.

## Seguridad

`NAN_KEY` vive solo en `.env` (ignorado por git) y nunca llega al cliente. La API no
guarda el texto de las noticias, solo un hash y los resultados. Ninguna salida contiene
cifras de estimación de voto.

## Ramas y flujo de trabajo

- `main`: estable y demostrable. Solo recibe merges desde `dev`, a mano.
- `dev`: integración. Los PRs apuntan aquí, nunca a `main`.
- Ramas de trabajo: `feature/<id>-<slug>`, `fix/*`, `chore/*`, `docs/*`.

Conventional Commits, un commit por unidad de trabajo con sus tests. Los detalles del
flujo (ODD, RDD, protecciones) están en la sección 15 de la ficha técnica.
