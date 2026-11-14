# ENC-09: Saneador de salida y detector independiente

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-09 | Saneador de salida y detector independiente | Cero fugas en la suite | **Alto** |

Sección 7.5:

> Regla dura, siempre activa e independiente de la veda: **ninguna parte de la respuesta
> contiene cifras de estimación de voto ni de escaños asociadas a una formación**.
>
> - Se enmascara cualquier frase de salida que combine una formación (de
>   `config/parties.yaml`) con un número, un porcentaje o la palabra "escaños". Se
>   sustituye por `[cifra de estimación omitida]`.
> - La API devuelve **posiciones** (`start`, `end`) en el texto de entrada, no copias de
>   frases. […]
> - Los hallazgos de margen y diferencia se expresan con razones (`r`), no con las cifras.
> - Test obligatorio: ninguna salida de la suite de evaluación pasa un detector
>   independiente de "formación + porcentaje".

Métrica de 11.3: **Fugas del saneador: 0 en toda la suite.**

## Objetivo
Garantizar que ninguna salida de la aplicación reproduzca una cifra de estimación de voto,
y demostrarlo con un detector construido de forma independiente.

## Problema y motivo
Es la obligación legal y ética del producto: reproducir una estimación de voto durante la
veda o fuera de contexto es exactamente lo que la herramienta denuncia. Además, un detector
que comparta el punto ciego del saneador reportaría "cero fugas" mientras la app filtra.

## Alcance
- Dentro: `sanitizer/mask.py` (`mask_vote_estimates`, `MASK`), `sanitizer/detector.py`
  (`find_leaks`), corpus adversarial y controles positivos.
- Fuera: aplicar el saneador al informe completo y a la persistencia (ENC-11), la veda
  (ENC-10), el corpus de evaluación real (ENC-16/17).

## Restricciones
- Independencia obligatoria: el detector **no** reutiliza el troceado de frases del
  saneador ni su lógica. Usa su propia ventana por terminadores (incluido el punto de
  `1.200`) y su propia gramática. Comparten la lista curada de formaciones, que es dato,
  no algoritmo.
- El saneador es selectivo: conserva la información técnica (muestras, márgenes,
  confianza) y elimina solo las frases con formación y cifra.
- El detector falla cerrado: una cifra desnuda en la misma cláusula que una formación
  cuenta como fuga, aunque sea inocente.
- Sin llamadas al modelo: saneado determinista y local (test que lee el propio fuente).

## Configuración de pruebas
- Modo TDD: activado (RED: `ModuleNotFoundError` en `ficha_tecnica.sanitizer`).
- Runner exacto: `cd server && uv run pytest tests/test_sanitizer.py tests/test_sanitizer_adversarial.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~330 con tests
- Slices: rama `feature/enc-09-sanitizer`

## Tareas
- [ ] ENC09-T1 `find_leaks` con controles positivos: si el detector no ve una fuga
  conocida, los tests de "cero fugas" no valen nada. Riesgo RDD: **alto**
- [ ] ENC09-T2 `mask_vote_estimates` enmascara la frase completa (nombre incluido) y
  conserva el resto del texto carácter a carácter. Riesgo RDD: **alto**
- [ ] ENC09-T3 Corpus adversarial de 12 formulaciones reales (porcentaje, "por ciento",
  escaños, diputados, actas, cifra antes o después del partido, mayúsculas, sin tildes,
  saltos de línea, varias formaciones). Riesgo RDD: **alto**
- [ ] ENC09-T4 Selectividad: una noticia larga pierde solo las frases con resultado.
  Riesgo RDD: alto
- [ ] ENC09-T5 Verificación, merge a `dev` y CI. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_sanitizer.py`: 8 controles positivos + 5 negativos | verdes | ver abajo |
| T2 | enmascarado, idempotencia, texto vacío, aislamiento del modelo | verdes | ver abajo |
| T3 | `tests/test_sanitizer_adversarial.py`: 12 formulaciones, todas enmascaradas, y control de que el detector las ve antes | verdes | ver abajo |
| T4 | noticia larga: conserva 2.000 entrevistas, 2,2 puntos y 95 %; elimina 34,2 % y 28,4 % | verde | ver abajo |
| T5 | `uv run pytest` (345), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |

### Límites declarados (no son fugas aceptadas)

1. **Cifra en la frase siguiente.** "Según el sondeo, el PP ganaría. Obtendría el 32 %."
   no se enmascara: el saneador trabaja frase a frase. Acotado a propósito porque las
   salidas son plantillas fijas sin cifras y la aritmética se expresa con razones; ampliar
   la ventana enmascararía frases no relacionadas. Hay un test que fija el comportamiento.
2. **"Ciudadanos" es también un sustantivo común.** "El 60 % de los ciudadanos cree…" se
   enmascara. Es el precio de fallar cerrado: una cifra perdida cuesta una frase, una
   cifra publicada cuesta el proyecto. Un heurístico de mayúsculas lo arreglaría y a la vez
   dejaría pasar prensa escrita en minúsculas. Test que lo documenta.

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | assess nativo no disponible en esta máquina | verificación del escritor: 345 tests, ruff, pyright, CI |

## Progreso
- Completa.

## Siguiente paso
ENC-10 (veda por fecha) y ENC-11 (API y persistencia sin texto), ambas de alto riesgo.
Después ENC-16/17 podrán correr el detector sobre la suite de evaluación completa.
