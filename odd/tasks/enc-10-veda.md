# ENC-10: Modo veda por fecha

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-10 | Modo veda por fecha | Simulación con `VEDA_NOW` y tests de borde | **Alto** |

Sección 7.6:

> La ley prohíbe publicar, difundir o reproducir sondeos electorales durante los cinco días
> anteriores a la votación. Aunque analizar una noticia no es publicarla, el diseño es
> **conservador**:
>
> ```yaml
> veda:
>   mode: strict          # strict | off
>   start: "2026-11-24T00:00:00+01:00"
>   end:   "2026-11-30T00:00:00+01:00"
>   block_if_p_electoral_at_least: 0.35
> ```
>
> En modo `strict` y dentro de la ventana, si `b_is_electoral` ≥ 0,35 o `b_poll_type`
> apunta a intención de voto, la API responde con un aviso de veda y **sin hallazgos**. Las
> encuestas de otros temas siguen analizándose. La ventana se lee de configuración, no del
> reloj del navegador. En la demo se puede simular con
> `VEDA_NOW=2026-11-25T10:00:00+01:00`.

La ventana exacta sigue `[VERIFICAR]` con la JEC (punto 4 de las verificaciones pendientes).

## Objetivo
Negarse a analizar encuestas electorales dentro de la ventana legal, con un aviso claro y
sin emitir hallazgos, y permitir simular la fecha para la demo.

## Problema y motivo
Equivocarse por una hora significa publicar un resultado cuando publicar está prohibido. Es
el único lugar donde la app decide **no** hacer su trabajo.

## Alcance
- Dentro: `policy/veda.py` (`VedaConfig`, `within_window`, `should_block`, `veda_notice`,
  `resolve_now`) y su integración en `PolicyConfig` y en `config/policy.yaml`.
- Fuera: la respuesta HTTP con la que la API devuelve el aviso (ENC-11).

## Restricciones
- Ventana **semiabierta**: `start` incluido, `end` excluido, para que el día de la votación
  siga cubierto y la reapertura sea exacta.
- Toda fecha debe llevar zona horaria; una fecha sin zona lanza error en vez de asumir una.
- La ventana se lee de configuración; el reloj del sistema solo aporta "ahora".
- El aviso no contiene cifras ni nombres de formaciones.
- `mode: off` desactiva la veda sin tocar nada más.

## Configuración de pruebas
- Modo TDD: activado (RED: `ModuleNotFoundError` en `ficha_tecnica.policy.veda`).
- Runner exacto: `cd server && uv run pytest tests/test_policy_veda.py`

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~300 con tests
- Slices: rama `feature/enc-10-veda`

## Tareas
- [ ] ENC10-T1 Ventana con bordes exactos por los dos lados, semiabierta, y equivalencia
  entre la hora local de la ventana y UTC. Riesgo RDD: **alto**
- [ ] ENC10-T2 `mode: off` no bloquea nunca. Riesgo RDD: alto
- [ ] ENC10-T3 `should_block`: umbral 0,35 inclusivo, intención de voto bloqueada aunque la
  probabilidad electoral sea baja, y otros temas analizables dentro de la ventana.
  Riesgo RDD: **alto**
- [ ] ENC10-T4 `VEDA_NOW` para la demo, con error explícito si falta zona horaria o el
  formato no es ISO 8601. Riesgo RDD: alto
- [ ] ENC10-T5 Verificación, merge a `dev` y CI. Riesgo RDD: bajo

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|
| T1 | `tests/test_policy_veda.py`: antes/justo en el inicio/en medio/último segundo/justo en el fin, y el mismo instante en UTC | verdes | ver abajo |
| T2 | `mode: off` con probabilidad 0,99 y tipo de intención de voto | verde | ver abajo |
| T3 | umbral 0,35 (sí) y 0,34 (no); intención de voto con p=0,10; encuesta de otros temas dentro de la ventana | verdes | ver abajo |
| T4 | `VEDA_NOW` válido, formato inválido, sin zona horaria, y sin override (reloj del sistema) | verdes | ver abajo |
| T5 | `uv run pytest` (364), `ruff check`, `ruff format --check`, `pyright` | verdes | ver abajo |
| Demo (17) | `VEDA_NOW` en 4 instantes: 23/11 nada, 25/11 y 29/11 solo electoral, 30/11 nada | correcto | ver abajo |

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|
| Slice completo | assess nativo no disponible en esta máquina | verificación del escritor: 364 tests, ruff, pyright, CI |

## Progreso
- Completa.

## Siguiente paso
ENC-11: API `/v1/analyses` y persistencia sin texto, que es donde la veda y el saneador se
aplican al informe completo.
