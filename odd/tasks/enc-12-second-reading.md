# ENC-12: Segunda lectura enfocada y zona gris

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-12 | Segunda lectura enfocada y zona gris | Los casos de zona gris pasan por la segunda lectura y, si persiste la duda, llegan a "Revisar" | Medio |

Sección 6.4:

> 1. Se pregunta a **Clef** una vez por grupo (A, B y, si hay preguntas citadas, C).
> 2. Si algún ítem queda en la zona gris `[0,20, 0,80]` y es de capa formal, se repite
>    **solo ese grupo** con una **segunda lectura enfocada**: el `state` se reduce a las
>    frases candidatas del ítem y a su contexto inmediato, que da menos ruido que el digest
>    completo.
> 3. Si sigue en zona gris: estado **Revisar**. No se fuerza una respuesta.

## Objetivo
Convertir una duda en una decisión, gastando una sola llamada extra y solo cuando hay algo
que decidir.

## Problema y motivo
Con una sola lectura, cualquier probabilidad intermedia termina en "revisar a mano". Con el
proveedor `mock` eso dejaba 11 de 15 ítems en revisión: una ficha que no dice nada. La
segunda lectura con menos ruido es lo que permite que el semáforo signifique algo.

## Alcance
- Dentro: `build_focused_digest` en `extractor/digest.py` y `_second_reading` en
  `api/pipeline.py`.
- Fuera: cambiar los umbrales (ENC-07) o el formato de la ficha.

## Restricciones
- Solo se repreguntan los ítems en duda y solo su grupo, con las preguntas recortadas a
  esos ítems.
- La capa que merece segunda lectura sale de configuración (`second_reading_for_layers`):
  una duda metodológica va directo a `review` sin gastar una llamada.
- Si no hay dudas, **no hay llamada**. Un test cuenta las llamadas.
- El presupuesto del digest enfocado es de 600 tokens, con recorte de contexto primero y de
  evidencia después.
- Sin evidencia del código, el digest enfocado sigue siendo válido: se pregunta igual.

## Configuración de pruebas
- Modo TDD: activado (RED: `ImportError: cannot import name 'build_focused_digest'`).
- Runner exacto: `cd server && uv run pytest tests/test_second_reading.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~330 con tests
- Slices: rama `feature/enc-12-second-reading`

## Tareas
- [ ] ENC12-T1 `build_focused_digest`: evidencia del ítem, frase anterior y siguiente como
  contexto, presupuesto de 600 tokens. Riesgo RDD: medio
- [ ] ENC12-T2 Confirma presente → `present`; confirma ausente → `absent`; duda que
  persiste → `review`. Riesgo RDD: **alto**
- [ ] ENC12-T3 Solo se repreguntan los ítems en duda; sin dudas no hay llamada; una duda
  metodológica no gasta llamada. Riesgo RDD: alto
- [ ] ENC12-T4 Verificación y merge. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_second_reading.py`: evidencia y contexto presentes, solo los ítems pedidos, ≤ 600 tokens, ítem sin evidencia no rompe | verdes | ver abajo |
| T2 | confirma presente (0,92), confirma ausente (0,04), duda persistente (0,48 → review) | verdes | ver abajo |
| T3 | solo los ítems en duda; sin dudas exactamente 2 llamadas; metodológica sin llamada extra | verdes | ver abajo |
| T4 | `uv run pytest` (403), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |

### Hallazgo del test de conteo de llamadas

`test_no_doubt_means_no_second_reading` esperaba 2 llamadas y encontró 3: el pipeline
preguntaba el **grupo B dos veces** fuera de la veda, una para el chequeo de veda y otra
dentro del `gather` paralelo. Corregido: ahora B se pregunta una sola vez y su respuesta se
reutiliza para decidir el encuadre y la veda. Efecto: una llamada menos por análisis en el
camino normal, que es el de la demo.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | assess nativo no disponible en esta máquina | verificación del escritor: 403 tests, ruff, pyright, CI |

## Progreso
- Completa.

## Siguiente paso
ENC-13 (modo URL con fetch seguro, alto riesgo) o ENC-14/15 (interfaz) si se prioriza la
demo visible.
