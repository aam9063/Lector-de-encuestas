# Ficha Técnica

Pegás una noticia sobre una encuesta y te dice, ítem por ítem, **qué información necesaria
para interpretarla aparece y cuál falta**. Clef decide qué hay en el texto; el código
comprueba la aritmética y las reglas.

No juzga si la encuesta es verdadera ni a favor de quién. No reproduce cifras de estimación
de voto. No aplica la ley: marca con la etiqueta `formal` los ítems que coinciden con el
artículo 69 de la LOREG y avisa en cada ficha de que la valoración jurídica corresponde a la
Junta Electoral Central.

Proyecto del hackathon #2 NaN "Decide con Clef". Diseño completo en
[`lector-de-encuestas.md`](./lector-de-encuestas.md); bitácora de desarrollo, decisiones y
errores en [`informe.md`](./informe.md).

## Arranque en 3 comandos

Necesitás Python 3.14 con [uv](https://docs.astral.sh/uv/) y Node 22 con
[pnpm](https://pnpm.io/).

```bash
# 1. La clave de NaN (la misma de los modelos de chat), en un .env que no se versiona
echo 'NAN_KEY=tu-clave-aqui' > .env

# 2. Backend con el modelo real
cd server && uv sync && uv run uvicorn ficha_tecnica.api.app:app --port 8000

# 3. Web, en otra terminal
pnpm --dir web install && pnpm --dir web dev
```

Abrí <http://127.0.0.1:5173>, pegá una noticia y pulsá **Analizar**. La web hace proxy de
`/v1` hacia el backend.

Sin clave en `.env` la app arranca igual, con el proveedor `mock` (respuestas planas), y la
ficha lo dice en el campo `provider`. Sirve para ver el flujo, no para medir nada.

## Qué devuelve

Una ficha con semáforo y quince ítems en dos bloques:

- **formal** (`formal`): lo que el artículo 69 de la LOREG pide publicar junto a la encuesta.
- **metodológico** (`methodological`): notas de guías profesionales. Nunca se presenta como
  incumplimiento.

Cada ítem tiene un estado —`present`, `absent`, `refers_external`, `review`—, el motivo en
una línea y **las posiciones del texto** donde está la evidencia. La interfaz resalta esas
posiciones sobre el texto que pegaste: la app nunca regenera la frase, solo señala dónde
mirar.

Cuatro estados del semáforo: `red` (falta un ítem formal de gravedad alta, o salta una regla
aritmética), `amber` (falta uno medio, hay ítems en revisión o salta un aviso), `green` (nada
de lo anterior) y `grey` (no parece una encuesta, o veda).

## Modos de entrada

- **Texto pegado** (principal). Se limpian artefactos de pegado (cercas de markdown) sin
  mover los índices, para que la evidencia siga apuntando al texto original.
- **URL** (secundario). Descarga segura: solo `http`/`https`, sin credenciales, todas las
  direcciones del host deben ser públicas, redirecciones revalidadas salto a salto, tope de
  bytes y de tiempo. Muchos medios bloquean clientes automatizados: si la descarga falla, se
  pega el texto.

## Medición

Corrida real contra Clef sobre 12 casos del corpus sintético, sistema completo:

| Métrica | Valor | Objetivo |
|---|---|---|
| Tasa de falsa acusación (ausente donde el gold dice presente) | **0,00 %** (0/165) | ≤ 2 % |
| Recall de omisiones reales | **86,67 %** | ≥ 85 % |
| Ítems en `review` | 10,00 % | ≤ 20 % |
| Exactitud de M4 y M5 | 1,000 | 100 % |
| Estabilidad entre corridas iguales | 1,000 | Clef ≈ 100 % |
| Fugas del saneador | **0** | 0 |
| Latencia p50 / p95 | 872 / 1294 ms | frente a jueces LLM |

El corpus, el harness y las métricas están en `server/src/ficha_tecnica/evaluation/`. Para
correrlo:

```bash
cd server && uv run python ../eval/run.py --limit 12 --baseline B4   # escribe eval/chart.svg
```

`--limit` es pequeño a propósito: cada caso consume dos o tres llamadas al modelo. B1 y B2
(los jueces LLM de la comparación) se reportan como **no disponibles**: no hay acceso a
modelos de chat configurado, y simular su latencia o su precisión fabricaría la conclusión.

## Reglas duras

| Regla | Cómo se garantiza |
|---|---|
| Ninguna salida reproduce cifras de estimación de voto | Saneador siempre activo, con un detector construido aparte para probarlo |
| Ningún hallazgo nombra una formación | Las plantillas de mensaje no las contienen, y se enmascara la frase completa |
| La noticia no se guarda | Solo un hash SHA-256; un test vuelca la base entera y busca fragmentos del texto |
| Una duda no se convierte en acusación | Con evidencia del código, un ítem **nunca** puede quedar `absent` |
| Dentro de la veda no se analizan encuestas electorales | Ventana configurable, con `VEDA_NOW` para simular la fecha |

## Desarrollo

```bash
cd server && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest
pnpm --dir web lint && pnpm --dir web typecheck && pnpm --dir web build
```

- Compuerta actual: **530 tests**, `ruff` y `pyright` en verde.
- CI (`.github/workflows/ci.yml`) corre lo mismo en cada push a `dev` y en cada PR.
- Documento de cada tarea en [`odd/tasks/`](./odd/tasks).
- `config/` contiene la checklist, el cuestionario, la política, la veda y las listas
  curadas de casas y formaciones.

## Estructura

```
server/    API de análisis (FastAPI) y lógica determinista
web/       Interfaz: pegar, ficha con semáforo, evidencia
config/    Checklist, cuestionario, política, veda, listas curadas
eval/      CLI del harness de evaluación
odd/tasks/ Documentos de feature
docs/      Contrato de la API de Clef y guion de demo
```

## Límites conocidos

- El modo URL depende de que el medio permita descarga automatizada.
- `config/pollsters.yaml` está a medio curar: Clef cubre las casas que la lista no conoce,
  pero la evidencia mostrada es más pobre.
- La ventana exacta de la veda está pendiente de confirmar con la JEC.
- El corpus de evaluación es sintético; no incluye noticias reales etiquetadas a mano.

## Ramas

`main` es lo entregable y solo recibe merges desde `dev`, a mano. `dev` integra; los PRs
apuntan ahí. Ramas de trabajo: `feature/<id>-<slug>`, `fix/*`, `docs/*`, `chore/*`.
