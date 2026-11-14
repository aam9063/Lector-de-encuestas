# ENC-01: Estructura del repo y arranque del proyecto

## Especificación (literal)

"Vamos a empezar el proyecto. Dentro tienes un md para que lo leas y veas en que consiste.
Crea toda la estrructura del proyecto y dime cuando creo el .env para poner la api key y
asi ya puedas trabajar en automatico. Tienes total libertad para pushear y mergear a dev.
Todo lo dejaras en dev hasta que yo abra pr a main. Sube todas las ramas al repo y sigue
buenas practicas de git"

Fuente: `lector-de-encuestas.md` (ficha técnica v2), secciones 13, 15 y 16 (ENC-01).

## Objetivo
Dejar el repositorio listo para trabajar: estructura completa (`server/`, `web/`, `config/`,
`eval/`, `odd/`, `docs/`), CI, githooks, plantillas y ramas `main`/`dev` en el remoto.

## Problema y motivo
El repo existe sin commits. Sin estructura ni CI no se puede empezar el núcleo (ENC-02+).

## Alcance
- Dentro: bootstrap git (main/dev), server con uv (paquete `ficha_tecnica` con módulos
  vacíos + health API), web con Vite/React 19/Tailwind v4, YAMLs v1 de config, CI, hooks,
  plantilla de PR, CODEOWNERS, README, `.env.example` y `.gitignore`.
- Fuera: implementación real de ENC-02+ (cliente Clef, extractor, política, saneador...),
  dataset de evaluación, pantallas de la web.

## Restricciones
- Base de todo PR: `dev`. Nada a `main` sin PR del usuario.
- Nunca versionar `.env` ni secretos (`NAN_KEY`).
- Conventional Commits, un commit por unidad de trabajo.
- Merge a `dev` con `--no-ff` (el usuario autorizó push y merge a dev explícitamente).

## Configuración de pruebas
- Modo TDD: excepción documentada (scaffold: no hay comportamiento pedible más allá de
  humo).
- Fuente de la decisión: tarea de bootstrap, riesgo bajo.
- Runner exacto: `uv run pytest`, `pnpm --dir web lint && pnpm --dir web typecheck && pnpm --dir web build`.

## Entrega
- Estrategia: ask-on-risk (rama única `chore/bootstrap`, sin slices).
- Líneas previstas: ~500 (mayoría generadas por scaffolders).
- Slices: un PR/rpush de `chore/bootstrap` a `dev` (merge directo autorizado por el usuario).

## Tareas
- [ ] ENC01-T1 Bootstrap git: commit inicial en `main` (ficha + .gitignore + .env.example), rama `dev`, push. Aceptación: `main` y `dev` en remoto. Riesgo RDD: bajo
- [ ] ENC01-T2 Scaffold `server/` con uv: paquete `ficha_tecnica` (schema, extractor, clef_client, policy, sanitizer, api) + tests de humo. Aceptación: `uv run pytest` verde, `uv run ruff check .` verde. Riesgo RDD: bajo
- [ ] ENC01-T3 Scaffold `web/`: Vite + React 19 + TSX + Tailwind v4 + proxy `/v1`. Aceptación: build y lint verdes. Riesgo RDD: bajo
- [ ] ENC01-T4 `config/` YAMLs v1: checklist, questionnaire, policy+veda, pollsters, parties. Aceptación: YAML válido, cargado por un test. Riesgo RDD: bajo
- [ ] ENC01-T5 CI, `.githooks/pre-push`, plantilla de PR, CODEOWNERS, README. Aceptación: workflow conforme a 15.9; hook bloquea push directo a main/dev. Riesgo RDD: bajo
- [ ] ENC01-T6 Merge `--no-ff` a `dev` y push de todas las ramas. Aceptación: `dev` en remoto con la estructura; CI en verde. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | push de `main` y `dev` | OK (a105915) | a105915 |
| T2 | `uv run pytest` (4), `ruff check`, `pyright` | verdes | bf54a18 |
| T3 | `pnpm lint` + `typecheck` + `build` | verdes | 2253ad5 |
| T4 | `uv run pytest` (8, incluye config YAMLs) | verde | 3ec050e |
| T5 | hook activo (`core.hooksPath=.githooks`), workflow conforme a 15.9 | OK | 7050a86 |
| T6 | merge `--no-ff` a `dev` + push de ramas | OK | ver `dev` |
| Extra | llamada real a Clef: contrato confirmado (noul/choice/score) | 200 OK, fixtures capturadas | 38581db |

Nota: `.env.example` fue bloqueado por la guarda de seguridad de Gentle AI (patrón
`.env*`), también en `git add`. Queda sin trackear en local; el `.gitignore` ya lo
negocia (`!.env.example`) por si se sube a mano. El `.env` real está ignorado.

Hallazgo: el `.env` exporta `NAN_API_KEY`, no `NAN_KEY`. `Settings` acepta ambos
(`AliasChoices`), cubierto por `tests/test_settings.py`.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | medium (`nativeRisk: unassessable`: binary missing) | diferido al cierre del slice; verificación del escritor en verde (pytest, ruff, pyright, build) |

## Progreso
- T1-T6 completas. Contrato de Clef confirmado contra la API real (verificación
  pendiente nº1 de la ficha, resuelta).

## Siguiente paso
ENC-02: `DecisionProvider` con adaptadores `nan` (semáforo de 2, reintento en 429) y
`mock`, con el parser escrito contra las fixtures capturadas.
