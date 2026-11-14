# ENC-02: DecisionProvider (nan y mock) y contrato de Clef

## Especificación (literal)

"Solo lectura. Explora <zona>..." — no aplica. La petición vigente es de la ficha técnica,
backlog ENC-02:

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-02 | `DecisionProvider`: cliente `nan` (semáforo de 2, reintento en 429) y `mock`. Primera llamada real y fixtures | Misma interfaz, parser probado con fixtures de respuesta real | Medio |

Autorización del usuario: "si si sigue" (tras proponer ENC-02).

## Objetivo
Una interfaz única hacia Clef con dos adaptadores intercambiables y un parser anclado al
formato real de respuesta.

## Problema y motivo
Sin este módulo la política no tiene de dónde leer probabilidades. El formato de respuesta
no estaba documentado (punto `[VERIFICAR]` nº1), así que el contrato se fijó con llamadas
reales en ENC-01 (`docs/clef-contract.md`, fixtures en `server/tests/fixtures/clef/`).

## Alcance
- Dentro: modelos Pydantic de respuesta y de pregunta, `DecisionProvider` (Protocol),
  `NanProvider` (semáforo global de 2, reintento inmediato en 429, mapeo de errores),
  `MockProvider` determinista, tests contra las tres fixtures reales.
- Fuera: digest builder (ENC-05), cuestionario (ENC-06), política (ENC-07), segunda
  lectura (ENC-12), cola multiusuario con límite por IP (ENC-18).

## Restricciones
- `NAN_KEY` solo en `.env`, nunca en logs ni fixtures.
- Máximo 2 peticiones en vuelo (límite de NaN). Reintento solo para 429.
- El parser no debe romperse si la API agrega campos: `extra="ignore"`.

## Configuración de pruebas
- Modo TDD: activado
- Fuente de la decisión: sección 15.3 de la ficha (TDD en `clef_client`)
- Runner exacto: `uv run pytest tests/test_clef_models.py tests/test_clef_nan.py tests/test_clef_mock.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas (sin generados): ~450
- Slices: un solo PR/rama `feature/enc-02-clef-provider`

## Tareas
- [ ] ENC02-T1 Modelos de pregunta y respuesta (`noul`, `choice`, `score`) con unión
  discriminada por `type`. Aceptación: las tres fixtures reales parsean y las
  probabilidades suman 1. Riesgo RDD: bajo
- [ ] ENC02-T2 `NanProvider`: cuerpo de petición correcto, Bearer, semáforo de 2,
  reintento inmediato en 429 hasta 5 intentos, mapeo 401/400/413/timeout. Aceptación:
  tests con `httpx.MockTransport`. Riesgo RDD: medio
- [ ] ENC02-T3 `MockProvider` determinista con la misma interfaz. Aceptación: dos
  llamadas iguales devuelven lo mismo; permite overrides por ítem. Riesgo RDD: bajo
- [ ] ENC02-T4 Verificación completa, commit de unidad de trabajo, merge a `dev` y CI
  en verde. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_clef_models.py` (6 tests contra las 3 fixtures reales) | 6 verdes | ver abajo |
| T2 | `tests/test_clef_nan.py` (8 tests: cuerpo, 429, 401, 400/413, timeout, semáforo) | 8 verdes | ver abajo |
| T3 | `tests/test_clef_mock.py` (5 tests: determinismo, suma 1, overrides) | 5 verdes | ver abajo |
| T4 | suite completa `uv run pytest` (34), ruff, pyright | verdes | ver abajo |
| Integración | 2 llamadas concurrentes reales a NaN con 5 preguntas (590 tokens) | 200 OK, idénticas entre sí | ver abajo |

Hallazgo de estabilidad: dos ejecuciones reales idénticas devolvieron exactamente las
mismas probabilidades (`Clef ≈ 100 %` de acuerdo, como preveía la sección 11.3).

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|

## Progreso
- T1-T4 completas y verificadas.

## Siguiente paso
ENC-05 (digest builder) y ENC-06 (cuestionario v1 con snapshot), o ENC-03 (parser
numérico y de fechas en español) según el orden del día 1.
