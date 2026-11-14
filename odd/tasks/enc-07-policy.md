# ENC-07: Política de estados con umbrales asimétricos

## Especificación (literal)

Backlog de la ficha técnica (`lector-de-encuestas.md`, sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-07 | Política de estados con umbrales asimétricos | Tabla 7.2 cubierta con tests, incluida M14 | **Alto** |

Sección 7.2, la tabla que esta tarea debe implementar íntegra:

| Candidato del código | p(presente) de Clef | Estado |
|---|---|---|
| Sí | ≥ 0,50 | **Presente** (código y Clef) |
| Sí | < 0,50 | Zona gris, segunda lectura |
| No | ≥ 0,80 | **Presente** (solo Clef) |
| No | ≤ 0,10 | **Ausente** |
| No | entre 0,10 y 0,80 | Zona gris, segunda lectura |
| Cualquiera | `a_external_sheet` ≥ 0,80 y p(ítem) < 0,50 | **Remite** a ficha externa |
| Zona gris tras la segunda lectura | | **Revisar** |

> Un ítem **Ausente** solo se marca así si además el código no encontró ni un solo
> candidato.

Sección 7.4, el semáforo:

| Resultado | Condición |
|---|---|
| Rojo | Falta algún ítem formal de gravedad alta, o salta M5 o M11 |
| Ámbar | Falta algún ítem formal de gravedad media, o hay ítems en Revisar, o saltan M4, M6, M7 o M9 |
| Verde | Nada de lo anterior |
| Gris | No es una encuesta (`not_a_poll`) o veda |

Y de 7.3, las banderas del grupo B: `headline_overreach_flag_min_score: 3`,
`prediction_flag_min_p: 0.70`, `subgroup_flag_min_p: 0.70`, `self_selected_flag_min_p: 0.60`.

## Objetivo
Traducir probabilidades y evidencia del código a estados por ítem, sin ambigüedad y con
la asimetría que protege al medio señalado, más el semáforo global.

## Problema y motivo
Es la pieza que decide si la app dice que a una noticia "le falta el tamaño de la
muestra". Acusar en falso es el fallo más caro del producto (sección 11.3: tasa de falsa
acusación ≤ 2 %), así que los umbrales son asimétricos y esta lógica debe ser explícita,
testeable y sin interpretaciones implícitas.

## Alcance
- Dentro:
  - `policy/config.py`: carga y valida `config/policy.yaml` (umbrales, bandas, banderas).
  - `policy/states.py`: `decide_item` (tabla 7.2) y `finalize_item` (zona gris tras la
    segunda lectura), con `needs_second_reading` como estado intermedio explícito.
  - `policy/semaphore.py`: `assign_semaphore` (tabla 7.4) y `group_b_flags` (banderas del
    grupo B).
- Fuera: orquestar la segunda lectura contra Clef (ENC-12), calcular M4/M5 (ENC-08),
  saneado (ENC-09), veda por fecha (ENC-10). El semáforo **recibe** las reglas disparadas
  como dato; no las calcula.

## Restricciones
- **Asimetría intocable**: con candidato del código, un ítem nunca puede quedar `absent`.
  Ausente exige que el código no haya encontrado nada *y* p ≤ 0,10.
- Umbrales desde configuración, no incrustados en la lógica; los valores por defecto
  coinciden con `config/policy.yaml` y un test lo comprueba.
- `absent` para un ítem `auxiliary` o `methodological` nunca produce rojo ni ámbar: solo
  cuentan los ítems formales (7.4).
- M6, M7 y M9 se mencionan en la tabla 7.4 pero **no están definidas en la ficha**. Se
  aceptan como identificadores disparados y se documenta que hoy están inertes: no se
  inventa su significado.
- Determinista, síncrono, sin red.

## Configuración de pruebas
- Modo TDD: activado.
- Runner exacto: `cd server && uv run pytest tests/test_policy_states.py tests/test_policy_semaphore.py tests/test_policy_config.py`
- Compuerta: `cd server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas: ~450
- Slices: rama `feature/enc-07-policy`.

## Tareas
- [ ] ENC07-T1 `policy/config.py` carga el YAML y expone los umbrales tipados; los
  defaults coinciden con el fichero. Riesgo RDD: medio
- [ ] ENC07-T2 `decide_item` cubre la tabla 7.2 completa, celda por celda, más el caso
  M14 (paráfrasis sin cambio de contenido: el código no encuentra candidato, Clef sí →
  `present`, nunca `absent`). Riesgo RDD: **alto**
- [ ] ENC07-T3 `finalize_item`: confirmación de la segunda lectura → `present`/`absent`;
  duda persistente → `review`. Riesgo RDD: **alto**
- [ ] ENC07-T4 `assign_semaphore` y `group_b_flags` según 7.4 y 7.3. Riesgo RDD: alto
- [ ] ENC07-T5 Verificación, merge a `dev` y CI. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_policy_config.py` (5): defaults == YAML, umbrales documentados, validación de umbrales incoherentes | verdes | ver abajo |
| T2 | `tests/test_policy_states.py` (36): tabla 7.2 celda por celda, incluida M14 y la propiedad "con candidato nunca ausente" | verdes | ver abajo |
| T3 | `tests/test_policy_states.py`: segunda lectura confirma → presente/ausente; duda persistente → revisar | verdes | ver abajo |
| T4 | `tests/test_policy_semaphore.py` (19): 7.4 y banderas del grupo B, reglas sin color documentadas como inertes | verdes | ver abajo |
| Compuerta | `uv run pytest` (243), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |
| Integración | escenario real: sin muestra → `absent` y semáforo rojo; candidato con duda → segunda lectura; duda persistente → `review`; veda → `grey` | correcto | ver abajo |

### Interpretaciones registradas

- Tras la segunda lectura **no queda otro paso**: un ítem con candidato del código y
  probabilidad baja termina en `review`, no en un tercer "volver a leer" ni en `absent`.
- Un `absent` de un ítem formal de gravedad **baja** no colorea el semáforo: la tabla 7.4
  solo asigna color a las ausencias altas y medias. Queda como test explícito para que el
  día que se decida lo contrario, el cambio sea visible.
- M6, M7 y M9 se aceptan como identificadores disparados pero **no se inventa su
  significado**; M12 y M13 tampoco tienen color asignado en 7.4 y quedan inertes.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|

## Progreso
- ENC07-T1 a T5 completas en línea, con 60 tests nuevos y verificación de integración.

## Siguiente paso
ENC-08: calculadora de margen (M4) y diferencia frente al margen (M5), que alimenta las
reglas rojas del semáforo.
