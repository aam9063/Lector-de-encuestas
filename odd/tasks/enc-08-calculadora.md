# ENC-08: Calculadora de margen y diferencia

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-08 | Calculadora de margen y diferencia | Tabla de `n` y casos límite de `r` | Medio |

Sección 7.3:

> **M4. Coherencia del margen.** Con muestreo aleatorio simple y confianza del 95 %, el
> margen máximo es `e = z * sqrt(0,25 / n)`, con `z = 1,96` (o 2,0 si el texto dice
> 95,5 %). […]
> - Si el margen declarado es **menor** que el 90 % del teórico para esa `n`: hallazgo
>   "margen más pequeño que el mínimo teórico con muestreo aleatorio simple". Es un aviso,
>   no un error […]
> - Si es **mayor**, es normal (efectos del diseño muestral) y no se marca.

> **M5. Diferencia frente al margen.** Con `lead` la diferencia entre las dos cifras más
> altas que cita el texto y `m` el margen declarado:
> | `r = lead / m` | Lectura |
> |---|---|
> | r < 1 | "La diferencia está dentro del margen" |
> | 1 ≤ r < 2 | "No concluyente según el criterio de AAPOR […]" |
> | r ≥ 2 | "Probablemente real, bajo los supuestos de muestreo aleatorio" |
>
> El hallazgo **M5** salta si `r < 2` y `b_lead_decisive` ≥ 0,70.

## Objetivo
Calcular en código el margen teórico, decidir si el declarado es inverosímil y clasificar
la diferencia entre las dos primeras fuerzas frente al margen. De aquí salen M4 y M5, que
son dos de las condiciones de semáforo rojo y ámbar.

## Problema y motivo
Es aritmética, no interpretación: la sección 3 dice "si se puede decidir con código, se
decide con código". Además el jurado mide la exactitud de M4 y M5 al 100 % sobre los
casos sintéticos (11.3), así que la tabla de `n` es un contrato verificable.

## Alcance
- Dentro: `policy/calculator.py` con `theoretical_margin`, `margin_is_implausible`,
  `lead_ratio`, `lead_verdict` y `fired_rules`; la tabla de `n` de la sección 7.3 como
  constante de referencia; los cuatro ajustes nuevos en `PolicyConfig` leídos del YAML.
- Fuera: extraer las cifras (ENC-03), el estado por ítem (ENC-07), redactar el mensaje
  (la plantilla es del informe) y la salida saneada (ENC-09).

## Restricciones
- Todo en `Decimal`, nunca `float`: un error de redondeo aquí mueve un hallazgo de lado a
  lado de un umbral.
- El módulo es puramente aritmético: **no importa el cliente de Clef** (hay un test que lo
  comprueba leyendo el propio fuente).
- M4 avisa, no acusa; un margen mayor que el teórico nunca se marca.
- Ante datos incompletos no se inventa: sin `n`, sin margen o sin `lead`, no hay hallazgo.

## Configuración de pruebas
- Modo TDD: activado (RED observado: primero `ModuleNotFoundError`, después 14 fallos por
  los campos que faltaban en `PolicyConfig`; GREEN después).
- Runner exacto: `cd server && uv run pytest tests/test_policy_calculator.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~380 con tests
- Slices: rama `feature/enc-08-calculadora`

## Tareas
- [ ] ENC08-T1 `theoretical_margin` reproduce la tabla de `n` fila por fila y usa z=2,0
  con 95,5 %. Riesgo RDD: medio
- [ ] ENC08-T2 M4: umbral del 90 % con el borde del lado seguro (2,52 no salta, 2,51 sí).
  Riesgo RDD: alto
- [ ] ENC08-T3 M5: `r` redondeado a un decimal y los tres tramos, con los bordes 1,0 y 2,0.
  Riesgo RDD: alto
- [ ] ENC08-T4 `fired_rules` combina ambos sin inventar: sin cifras no hay hallazgo; el
  titular no decisivo silencia M5. Riesgo RDD: alto
- [ ] ENC08-T5 Verificación, merge a `dev` y CI. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_policy_calculator.py`: 9 filas de la tabla + z de 95,5 % + monotonía + n=0 | verdes | ver abajo |
| T2 | M4: sospechoso, normal, y el borde 2,52 / 2,51 | verdes | ver abajo |
| T3 | M5: tabla de `r` con 5 casos y los tres tramos con sus bordes | verdes | ver abajo |
| T4 | `fired_rules`: sin cifras, M4 solo, M5 solo, titular no decisivo, diferencia amplia, ambos | verdes | ver abajo |
| T5 | `uv run pytest` (277), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |
| Aislamiento | el fuente de `calculator.py` no menciona `clef_client` | verde | ver abajo |

Nota de proceso: como en ENC-03, el documento se escribió al final y el código se escribió
antes de los tests en el primer intento; el módulo se apartó y se recuperó el RED real
antes de continuar.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | assess nativo no disponible en esta máquina | verificación del escritor: 277 tests, ruff, pyright, CI |

## Progreso
- Completa.

## Siguiente paso
Con ENC-08 cierra el hito del día 1. Sigue ENC-09 (saneador, alto riesgo) y ENC-10 (veda,
alto riesgo), y después la API (ENC-11).
