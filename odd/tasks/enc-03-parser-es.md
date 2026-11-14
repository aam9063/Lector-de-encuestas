# ENC-03: Parser numérico y de fechas en español

## Especificación (literal)

Backlog ENC-03 de la ficha técnica:

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-03 | Parser numérico y de fechas en español | `1.200`, `2,8 %`, "del 3 al 9 de noviembre" cubiertos con tests | Medio |

Autorización del usuario: "Tienes total libertad [...] y asi ya puedas trabajar en
automatico" (arranque del proyecto) más la indicación de seguir con el backlog.

## Objetivo
Convertir cifras y fechas en español a valores tipados (`Decimal`, `int`, `date`) con
reglas estrictas, para que la aritmética de márgenes y diferencias (ENC-08) no dependa
de formato ni de interpretación.

## Problema y motivo
`1.200` en España son mil doscientos, no uno coma dos. Leerlo mal convierte una muestra
de 1.200 personas en una de 1,2 y produce hallazgos aritméticos falsos, que es el peor
error posible en esta herramienta.

## Alcance
- Dentro: `parse_spanish_number`, `parse_percentage`, `parse_margin_figure`,
  `parse_date`, `parse_date_range`, `extract_sample_size`, `extract_margin`,
  `extract_confidence`, con nombres de mes y abreviaturas.
- Fuera: extracción de entidades y candidatos por ítem (ENC-04), digest (ENC-05),
  reglas aritméticas M4/M5 (ENC-08).

## Restricciones
- Una cifra desnuda nunca es un margen ni una muestra: cada extractor exige una pista
  cercana ("margen", "entrevistas", "confianza"). Ante la duda devuelve `None`; nunca
  adivina.
- Aritmética en `Decimal`, no en `float`.

## Configuración de pruebas
- Modo TDD: activado
- Fuente de la decisión: sección 15.3 (TDD en `extractor`)
- Runner exacto: `uv run pytest tests/test_extractor_numbers.py tests/test_extractor_dates.py tests/test_extractor_metrics.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas (sin generados): ~400
- Slices: una rama `feature/enc-03-parser-es`

## Tareas
- [ ] ENC03-T1 Números y porcentajes en formato español, incluido `±2,8` sin `%`.
  Riesgo RDD: bajo
- [ ] ENC03-T2 Fechas y rangos de campo, con abreviaturas, meses cruzados y cambio de
  año. Aceptación: el rango invertido devuelve `None`. Riesgo RDD: bajo
- [ ] ENC03-T3 Extracción de muestra, margen y confianza con pistas. Aceptación: una
  cuota de voto nunca se lee como muestra ni como margen. Riesgo RDD: medio
- [ ] ENC03-T4 Verificación, merge a `dev` y CI en verde. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_extractor_numbers.py` (20 casos) | verdes | ver abajo |
| T2 | `tests/test_extractor_dates.py` (13 casos) | verdes | ver abajo |
| T3 | `tests/test_extractor_metrics.py` (25 casos) | verdes | ver abajo |
| T4 | suite completa `uv run pytest` (92), ruff, pyright | verdes | ver abajo |
| Humo | 3 noticias simuladas: extrae 1200/2,8/95 y 2000/4, y descarta la votación abierta | correcto | ver abajo |

Nota de proceso: este documento se escribió después del código por un descuido de orden
en el flujo ODD; el contenido y la evidencia son los reales.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | pendiente de assess | ver PR/CI |

## Progreso
- T1-T4 completas y verificadas.

## Siguiente paso
ENC-05 (digest acotado) y ENC-06 (cuestionario v1 con snapshot), después ENC-07/08 sobre
la política y la calculadora.
