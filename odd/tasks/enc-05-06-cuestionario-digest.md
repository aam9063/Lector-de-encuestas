# ENC-05 + ENC-06: Cuestionario v1 cargado desde YAML y digest acotado

Una sola unidad de entrega: el cuestionario define los grupos (A, B, C) y el digest los
rellena. El test de presupuestos necesita el cuestionario cargado, así que separarlos
obligaría a un test que lea YAML a mano.

## Especificación (literal)

Backlog de la ficha técnica (`lector-de-encuestas.md`, sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-05 | Digest builder acotado | Presupuestos de tokens respetados en los tres grupos | Medio |
| ENC-06 | Cuestionario Clef v1 y snapshot | Snapshot del cuestionario y del `state` | Medio |

Sección 6.2 (el `state` que se envía a Clef):

> El texto se acota: Clef admite unos 16k tokens, pero menos ruido da mejores decisiones
> y menos latencia. `state` es una cadena: cada digest se serializa a JSON compacto antes
> de enviarlo. El digest A mezcla titular, arranque y las frases con dígitos o palabras
> clave (muestra, entrevist, margen, error, campo, encuesta, ficha, universo, confianza),
> sin duplicados:
>
> ```json
> {
>   "headline": "...",
>   "lede": "...maximo 120 tokens...",
>   "technical_sentences": ["...", "..."],
>   "meta": { "language": "es", "chars": 4210, "digest_tokens": 880 }
> }
> ```
>
> | Digest | Contenido | Presupuesto |
> |---|---|---|
> | A (ficha técnica) | Titular, arranque, frases técnicas | 1.200 tokens |
> | B (tipo y encuadre) | Titular, arranque, hasta 6 frases con cifras (en el interior, **sin sanear**, porque el saneado solo afecta a la salida) | 500 tokens |
> | C (redacción) | Preguntas citadas | 400 tokens |

Sección 6.3: los grupos A, B y C del cuestionario v1 viven en
`config/questionnaire.v1.yaml` (ya existe, 23 preguntas: 15 + 6 + 2).

## Objetivo
1. Cargar `config/questionnaire.v1.yaml` a objetos de pregunta **tipados**, reutilizando
   los modelos de `ficha_tecnica.clef_client.models` (`NoulQuestion`, `ChoiceQuestion`,
   `ScoreQuestion`), con grupos por nombre.
2. Construir los tres digests acotados de un texto y serializarlos como el `state` que se
   envía a Clef, respetando los presupuestos de tokens.

## Problema y motivo
Sin cuestionario tipado, la política no puede recorrer los ítems de forma genérica, y un
error de nombre de campo solo aparecería con un 400 de la API en producción. Sin digest
acotado se envía el texto entero y se degrada la latencia y la decisión.

## Alcance
- Dentro:
  - `schema/questionnaire.py`: `load_questionnaire()` → grupos con preguntas tipadas;
    versión; validación de que cada pregunta del YAML produce un modelo válido.
  - `extractor/digest.py`: `estimate_tokens`, `build_digest_a`, `build_digest_b`,
    `build_digest_c`, `build_state`.
  - Snapshot del cuestionario serializado y de los tres digests para un texto fijo.
- Fuera: llamar a Clef (hecho en ENC-02), política (ENC-07), saneado (ENC-09), recorte de
  frases candidatas por ítem (ya existe en ENC-04).

## Restricciones
- Determinista, síncrono, sin red.
- `state` es una **cadena**: `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`.
- El digest **B va sin sanear**: el saneado es solo de salida (sección 7.5). No importar
  nada de `sanitizer`.
- Los presupuestos son un techo duro: si al añadir una frase se supera, se deja fuera. No
  se corta una frase a la mitad, salvo el `lede`, que se recorta en límite de palabra.
- Sin dependencias nuevas: el conteo de tokens es una **aproximación documentada**
  (caracteres / 4, techo), no un tokenizer real. Documentarlo en el docstring y en el
  documento de feature. Si algún día hace falta exactitud, se sustituye solo esa función.
- No romper nada existente de `extractor` ni de `clef_client`.

## Configuración de pruebas
- Modo TDD: activado.
- Runner exacto: `cd server && uv run pytest tests/test_questionnaire.py tests/test_extractor_digest.py`
- Compuerta completa: `cd server && uv run ruff check . && uv run ruff format . && uv run pyright && uv run pytest`
- Snapshots: ficheros en `server/tests/fixtures/snapshots/`. Escribirlos con el valor real
  que produce el código **después** de revisar a mano que el contenido es el correcto (no
  aceptar el snapshot a ciegas).

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas (sin generados): ~450
- Slices: una rama `feature/enc-05-06-digest` (ya creada). **No** comitear, **no**
  pushear, **no** fusionar.

## Tareas
- [ ] ENC05-T1 `load_questionnaire()` con grupos tipados y versión. Aceptación: los tres
  grupos cargan; 15 + 6 + 2 preguntas; una pregunta `choice` expone `criteria` como dict y
  una `score` como lista ordenada; un YAML con un tipo desconocido falla con error claro.
  Riesgo RDD: bajo
- [ ] ENC05-T2 Snapshots: cuestionario serializado estable, y el `state` de los tres
  digests para un texto fijo. Aceptación: el snapshot existe, está versionado y reproduce
  exactamente. Riesgo RDD: bajo
- [ ] ENC05-T3 `estimate_tokens` y digests A/B/C con techo duro. Aceptación: con un texto
  enorme, cada digest queda por debajo de su presupuesto (1.200 / 500 / 400) y `meta`
  informa `chars` y `digest_tokens` reales. Riesgo RDD: medio
- [ ] ENC05-T4 Contenido correcto de cada digest: A lleva titular, arranque y frases
  técnicas sin duplicados; B lleva hasta 6 frases con cifras y **no** está saneado; C
  lleva solo preguntas citadas. Aceptación: un texto con un porcentaje de una formación
  aparece íntegro en B. Riesgo RDD: medio

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_questionnaire.py` (6): grupos tipados, 15+6+2, tipo desconocido falla | verdes | ver abajo |
| T2 | 4 snapshots en `tests/fixtures/snapshots/`, revisados a mano contra la tabla 6.2 | aceptados | ver abajo |
| T3 | `tests/test_extractor_digest.py` (8) + `tests/test_extractor_digest_limits.py` (10) | verdes | ver abajo |
| T4 | contenido de A/B/C, B sin sanear, preguntas citadas | verdes | ver abajo |
| Compuerta | `uv run pytest` (188), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |

### Aproximación de tokens (documentada)

`estimate_tokens(text) = ceil(len(text) / 4)`. Un token por cada cuatro caracteres, sin
tokenizer real: determinista, sin dependencias nuevas y suficiente para acotar el ruido
que se envía a Clef. El presupuesto se comprueba sobre el **state serializado completo**,
incluido su propio `meta`, y el conteo se refina hasta que deja de moverse. Si algún día
hace falta exactitud, se sustituye **solo** esa función: nada más depende de la constante.

### Decisiones de revisión del padre

- Presupuestos como techo duro verificado con un texto de más de 40.000 caracteres: A, B
y C quedan por debajo de 1.200 / 500 / 400.
- Verificado que el digest B llega a Clef **sin enmascarar** la cifra de estimación: el
  saneado es de salida (7.5) y sanear la entrada ocultaría justo el dato que se juzga.
- `build_digest_c` lee la pregunta de **dentro de las comillas** y no de las frases
  troceadas: `split_sentences` termina la frase en el `?`, así que una pregunta entre
  comillas nunca es una frase entera. Decisión aceptada y documentada en el módulo.
- La frase de arranque cae en `lede`, no en la lista de frases con cifras; el invariante
  de "sin sanear" se comprueba sobre el digest completo, no sobre un campo concreto.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|

## Progreso
- T1-T4 entregadas por el worker, snapshots revisados a mano y verificadas por el padre
  con 10 tests de límites propios (texto enorme, vacío, sin cifras, pregunta citada,
  cifra sin enmascarar, JSON compacto).

## Siguiente paso
Comitear, fusionar a `dev`, push y CI. Después ENC-07 (política, alto riesgo).

## Contexto de arranque para el worker

Repositorio: `C:/Users/alber/orca/Lector-de-encuestas`. Rama ya creada y activa:
`feature/enc-05-06-digest`.

Ficheros existentes que hay que respetar y reutilizar:
- `server/src/ficha_tecnica/clef_client/models.py`: `NoulQuestion`, `ChoiceQuestion`,
  `ScoreQuestion`, `Question`. Úsalos tal cual; no dupliques modelos.
- `server/src/ficha_tecnica/extractor/candidates.py`: `split_sentences` (con posiciones
  sobre el texto original) y `_fold` (plegado de tildes 1:1).
- `server/src/ficha_tecnica/extractor/metrics.py` y `numbers.py`: ya extraen muestra,
  margen, confianza y porcentajes. No los dupliques.
- `config/questionnaire.v1.yaml`: la fuente del cuestionario.

Contrato de tipos de pregunta (verificado contra la API real, `docs/clef-contract.md`):
`noul` solo `instructions`; `choice` con `criteria` como **objeto** etiqueta→descripción;
`score` con `criteria` como **lista ordenada** de niveles.

Convenciones: Python 3.14, pyright standard, ruff line-length 100, docstrings y comentarios
en inglés, tests en `server/tests/test_*.py`.
