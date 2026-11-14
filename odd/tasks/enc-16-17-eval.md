# ENC-16 + ENC-17: Dataset sintético con mutaciones y harness de baselines

Una sola unidad: el dataset y el harness que lo consume. El dataset sin harness no mide
nada y el harness sin dataset no corre.

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-16 | Generador de artículos base y mutaciones | 40 bases y 240 casos con etiquetas | Medio |
| ENC-17 | Harness de evaluación y baselines B0 a B4 | `uv run python eval/run.py` genera tabla y gráfica | Medio |

Sección 11.1 (etiquetas por construcción):

> 1. Se generan **40 artículos base completos** con un modelo de NaN, en cuatro estilos
>    (agencia, diario local, resumen de televisión, hilo de red social). Cada uno incluye
>    todos los ítems de la ficha técnica.
> 2. **Todas las entidades y formaciones son ficticias** […] y cada texto lleva la marca
>    "SIMULACIÓN". […]
> 3. A cada base se le aplican **mutaciones** que cambian de forma conocida las etiquetas:
>    M1-M9 eliminan un ítem formal; M10 margen a la mitad del mínimo teórico; M11 titular
>    como victoria clara; M12 resultados como predicción; M13 votación abierta de lectores;
>    M14 paráfrasis sin cambio de contenido (las etiquetas **no** cambian); M15 sustituye
>    la ficha por un enlace.
> 4. Un conjunto de 20 a 25 noticias reales se etiqueta a mano **solo con URL y etiquetas**.

Sección 11.2, baselines:

| Id | Sistema |
|---|---|
| B0 | Solo reglas y expresiones regulares |
| B1 | LLM de NaN como juez con la misma lista, sin razonamiento |
| B2 | LLM de NaN con razonamiento alto |
| B3 | Reglas más Clef con una sola lectura |
| B4 | Reglas más Clef con segunda lectura enfocada (sistema completo) |

Sección 11.3, métricas: tasa de falsa acusación (≤ 2 %), recall de omisiones (≥ 85 %),
F1 por ítem, fracción de ítems en Revisar (≤ 20 %), exactitud de M4/M5, calibración,
estabilidad, latencia p50/p95 y **fugas del saneador: 0**.

## Objetivo
Producir, sin depender de un modelo generador, un corpus con etiquetas correctas por
construcción, y un harness que mida los baselines y saque la tabla y la gráfica de la demo.

## Problema y motivo
Sin esto la diapositiva más fuerte del pitch no existe: "mismo o mejor criterio, mucho más
rápido y repetible". Y sin etiquetas por construcción no hay forma de medir la falsa
acusación, que es el error que más caro cuesta.

## Alcance
- Dentro:
  - `server/src/ficha_tecnica/evaluation/`: generador del dataset (bases y mutaciones),
    etiquetas por construcción, baselines, métricas, salida en tabla y gráfica.
  - `eval/run.py`: CLI fino que delega en el paquete.
  - Tests del generador y de las métricas.
- Fuera: las 20-25 noticias reales etiquetadas a mano (no hay fuentes ni tiempo), B1 y B2
  como jueces LLM (no hay acceso a modelos de chat configurado; se reportan como **no
  disponibles**, nunca se simulan), el panel interno de la interfaz.

## Restricciones
- **Nada de generar artículos con un modelo por defecto.** El dataset se genera de forma
  determinista desde plantillas: reproducible, gratis y versionable. Documentar que la
  ficha preveía un modelo generador y por qué se elige esto (coste, reproducibilidad,
  revisión del corpus).
- Todo texto sintético empieza por `SIMULACIÓN`, con entidades ficticias ("Demoscopia
  Ficticia S.L.", "Partido Cohete", "Partido Brújula"). Nunca nombres reales.
- **Las etiquetas se calculan, no se escriben a mano**: cada mutación declara qué ítem
  cambia y en qué dirección; el caso guarda el gold derivado.
- **M14 no cambia etiquetas**: es el medidor de falsa acusación. Un test debe comprobar
  que el gold de la base y el de su M14 son idénticos.
- B1 y B2 se reportan como `unavailable` con una razón, no como si midieran.
- El harness debe permitir acotar: `--limit N` obligatorio por defecto pequeño (por costo
  de API), y `--baseline`. Nunca lanzar cientos de llamadas por defecto.
- La tasa de falsa acusación se calcula **solo** sobre ítems cuyo gold es `present`.
- Cero fugas: toda salida del harness pasa por `find_leaks` y el informe incluye el
  recuento (debe ser 0).
- La gráfica se genera como SVG autónomo (sin dependencias nuevas).

## Configuración de pruebas
- Modo TDD: activado para el generador y las métricas (no para la CLI).
- Runner exacto: `cd server && uv run pytest tests/test_evaluation_dataset.py tests/test_evaluation_metrics.py`
- Compuerta: `cd server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas: ~900 con tests
- Slices: rama `feature/enc-16-17-eval` (ya creada). **No** comitear, **no** pushear.

## Tareas
- [ ] ENC16-T1 Generador de bases: 40 artículos (10 plantillas × 4 estilos), todos los
  ítems presentes, entidades ficticias, marca SIMULACIÓN. Aceptación: 40 bases únicas y
  deterministas con semilla fija.
- [ ] ENC16-T2 Mutaciones M1-M15 con gold por construcción; separación dev/test **por
  artículo base**, no por caso. Aceptación: ~240 casos; M14 con gold idéntico a su base.
- [ ] ENC17-T1 Baselines B0 (reglas) y B3/B4 (Clef con una y dos lecturas) sobre el mismo
  pipeline. Aceptación: B4 usa `analyze` completo; B3 usa una sola lectura;
  B1/B2 `unavailable` con razón.
- [ ] ENC17-T2 Métricas: falsa acusación, recall, F1 por ítem, fracción en revisar,
  exactitud de M4/M5, latencia p50/p95, fugas del saneador.
- [ ] ENC17-T3 Salida: tabla en Markdown y gráfica SVG de falsa acusación contra latencia.
- [ ] ENC17-T4 `eval/run.py` como CLI fino y verificación de la compuerta completa.

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|

## Progreso
- Delegado al worker.

## Siguiente paso
Revisión del padre, ejecución real con un límite pequeño, commit y merge.

## Contexto de arranque para el worker

Repositorio: `C:/Users/alber/orca/Lector-de-encuestas`. Rama ya activa:
`feature/enc-16-17-eval`.

Piezas que ya existen y hay que reutilizar (no dupliques lógica):
- `ficha_tecnica.api.pipeline.analyze(text, provider=..., policy=..., now=..., provider_name=..., calls=...)`
  → devuelve un `Report` con `findings` (item_id, status, probability, evidence), `semaphore`,
  `computation`, `latency_ms`.
- `ficha_tecnica.clef_client.MockProvider` (sin red, determinista, con overrides por ítem)
  y `NanProvider` (real, semáforo de 2).
- `ficha_tecnica.policy.load_policy()` y `ficha_tecnica.schema.checklist.load_checklist()`.
- `ficha_tecnica.sanitizer.find_leaks` para el recuento de fugas.
- `docs/clef-contract.md` para el contrato real del modelo.

Para B3 (una sola lectura) añade a `analyze` un parámetro opcional
`second_reading: bool = True`; con `False`, los ítems en duda se quedan en `review` sin
llamada extra. No cambies el comportamiento por defecto.

El proveedor real se construye con `ficha_tecnica.api.app.build_provider()`. Para el
harness, si no hay clave, corre con el mock y dilo en el informe (`provider: mock`) en vez
de fingir resultados reales.

Convenciones: Python 3.14, pyright standard, ruff line-length 100, docstrings y comentarios
en inglés, copia de la CLI en español.
