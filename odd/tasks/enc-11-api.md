# ENC-11: API `/v1/analyses` y persistencia sin texto

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-11 | API `/v1/analyses` y persistencia sin texto | Ningún texto de noticia en la base (test) | **Alto** |

Sección 9:

> El sistema **no guarda el texto de las noticias**. Guarda un hash, la configuración usada
> y los resultados.

> `raw_answers_json` guarda **solo probabilidades**, nunca el digest.

Sección 8, endpoints: `POST /v1/analyses`, `GET /v1/analyses/:id`,
`POST /v1/analyses/:id/feedback`, `GET /v1/checklist`, `GET /v1/config`, `GET /v1/health`.

## Objetivo
Convertir las piezas deterministas y el cliente de Clef en una ficha servida por HTTP, con
persistencia de resultados y sin guardar nunca la noticia.

## Problema y motivo
Es el punto donde una promesa de privacidad se puede romper sin que nadie lo note: basta
con un campo de más en una tabla. Por eso hay un test que abre el SQLite y busca el texto
en cada fila de cada tabla, en vez de confiar en la lectura del código.

## Alcance
- Dentro: `schema/report.py` (modelos del informe), `schema/checklist.py` (checklist
  tipada), `api/pipeline.py` (orquestación), `api/store.py` (SQLite), `api/app.py` (rutas).
- Fuera: modo URL y fetch seguro (ENC-13), segunda lectura enfocada (ENC-12), panel de
  evaluación y `/v1/eval/run` (ENC-17), límite de peticiones por IP (ENC-18).

## Restricciones
- **Ningún campo puede contener el texto.** El modelo `Report` no tiene campo de texto y un
  test lo verifica con una lista de nombres prohibidos.
- Las posiciones de evidencia son índices sobre el texto original, no copias.
- La persistencia solo recibe el informe y probabilidades; ningún método acepta el texto.
- SQLite en un hilo aparte (`asyncio.to_thread`) para no bloquear el bucle que espera a Clef.
- Dentro de la veda solo se consulta el grupo B, y si se bloquea se devuelve aviso sin
  hallazgos: una noticia rechazada cuesta una llamada, no tres.

## Configuración de pruebas
- Modo TDD: activado (RED: `ModuleNotFoundError` en `ficha_tecnica.api.pipeline` y en
  `schema.report`).
- Runner exacto: `cd server && uv run pytest tests/test_pipeline.py tests/test_api_analyses.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~700 con tests
- Slices: rama `feature/enc-11-api`

## Tareas
- [ ] ENC11-T1 Modelos del informe sin campo de texto, con hash. Riesgo RDD: **alto**
- [ ] ENC11-T2 Pipeline: candidatos → digests → grupos A/B en paralelo → estados →
  aritmética → semáforo. Riesgo RDD: **alto**
- [ ] ENC11-T3 Persistencia sin texto, verificado abriendo el fichero SQLite. Riesgo RDD:
  **alto**
- [ ] ENC11-T4 Rutas `/v1/analyses` (POST/GET), feedback, `config`, `checklist`, `health`
  con validación de texto vacío (422) y excesivo (413). Riesgo RDD: alto
- [ ] ENC11-T5 Verificación y merge. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `test_the_report_model_has_no_field_for_the_news_text`, hash de 64 caracteres | verdes | ver abajo |
| T2 | `tests/test_pipeline.py` (14): 15 hallazgos, estados, spans recortables, aritmética, veda, not_a_poll, texto vacío | verdes | ver abajo |
| T3 | `test_the_news_text_is_never_written_to_the_database`: volcado de todas las tablas y todas las filas | verde | ver abajo |
| T4 | `tests/test_api_analyses.py` (15): POST/GET/feedback/config/checklist, 404, 422, 413 | verdes | ver abajo |
| T5 | `uv run pytest` (393), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |
| Humo real | POST contra la app: ficha ámbar, 15 hallazgos, 1.200 → margen teórico 2,8, `r` = 1,4, y "Demoscopia" ausente del fichero SQLite | correcto | ver abajo |

### Decisiones registradas

- **Sin segunda lectura todavía**: un ítem en zona gris se muestra como `review`. Es la
  lectura honesta mientras ENC-12 no exista, y es el estado que el diseño pide en caso de
  duda. Efecto visible con el proveedor `mock`: 11 de 15 ítems quedan en revisión porque el
  mock responde 0,5 a todo.
- **`fired` acepta reglas sin color**: M12 y M13 se calculan pero no colorean el semáforo,
  porque la tabla 7.4 no les asigna color. Documentado ya en ENC-07.
- **URL devuelve 501** con un mensaje explícito en vez de fallar de forma confusa: el modo
  URL es ENC-13 y el `fetch` seguro no existe aún.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | assess nativo no disponible en esta máquina | verificación del escritor: 393 tests, ruff, pyright, CI |

## Progreso
- Completa.

## Siguiente paso
ENC-12 (segunda lectura enfocada), que reduce los ítems en revisión, y ENC-14/15 (interfaz).
