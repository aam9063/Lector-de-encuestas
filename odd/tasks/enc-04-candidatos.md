# ENC-04: Extractor de candidatos por ítem y listas de entidades

## Especificación (literal)

Backlog ENC-04 de la ficha técnica (`lector-de-encuestas.md`, sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-04 | Extractor de candidatos por ítem y listas de entidades | Candidatos con posición para los ítems P0 | Medio |

Y de las secciones 5.2 y 6.1:

> Extractor de candidatos: Localiza frases candidatas por ítem y entidades de una lista
> curada.

> El resultado son **candidatos por ítem**: frases con posición. No se interpreta nada
> todavía.

> | Entidades | Lista curada de casas encuestadoras y organismos (`config/pollsters.yaml`,
> **a mantener y revisar**) y patrones "realizada por", "encargada por" |
> | Cifras de estimación | Un porcentaje o número de escaños junto a una formación de
> `config/parties.yaml` (lista completa, trato idéntico) |

## Objetivo
Dado un texto libre, localizar tres cosas con posiciones (`start`/`end` en el texto
original):

1. entidades de las listas curadas (casas encuestadoras y formaciones políticas);
2. cifras de estimación de voto (una formación junto a un número, un porcentaje o la
   palabra "escaños"), porque el saneador de ENC-09 las va a enmascarar;
3. frases candidatas por ítem de la checklist v1, para que la política tenga evidencia
   que mostrar.

## Problema y motivo
Clef no devuelve posiciones de texto. La evidencia que ve el usuario son las frases que
selecciona el código (sección 6.4, punto 4). Sin posiciones no hay resaltado en la
interfaz (ENC-15) ni saneador posible (ENC-09).

## Alcance
- Dentro:
  - `extractor/entities.py`: carga de `config/pollsters.yaml` y `config/parties.yaml`;
    búsqueda de entidades sin distinguir mayúsculas y con límites de palabra; un
    porcentaje o "escaños" junto a una formación devuelve un span de estimación.
  - `extractor/candidates.py`: troceado de frases en español con posiciones, y conjunto
    de pistas por ítem de la checklist; devuelve las frases candidatas de cada ítem.
- Fuera: digest (ENC-05), saneado (ENC-09), cálculo de márgenes (ENC-08), llamadas a
  Clef. **No** se interpreta nada: solo se localiza.

## Restricciones
- Nada de red, nada de Clef: módulo puramente determinista y sin `async`.
- Las posiciones son índices sobre el texto **original sin normalizar**. Quien consuma
  los spans recorta del texto que el usuario pegó.
- Trato idéntico a todas las formaciones: ninguna regla especial por partido.
- Ante ambigüedad, devolver menos candidatos, nunca inventar. Un ítem sin candidatos es
  un resultado válido y la política lo contempla.
- No romper las funciones ya existentes de `extractor` (numbers, dates, metrics).

## Configuración de pruebas
- Modo TDD: activado. Cada regla pedida con un test que primero falla.
- Fuente de la decisión: sección 15.3 (TDD en `extractor`).
- Runner exacto: `cd server && uv run pytest tests/test_extractor_entities.py tests/test_extractor_candidates.py`
- Comprobación completa antes de entregar: `cd server && uv run ruff check . && uv run ruff format . && uv run pyright && uv run pytest`

## Entrega
- Estrategia: ask-on-risk
- Líneas previstas (sin generados): ~400
- Slices: una rama `feature/enc-04-candidatos` (ya creada). **No** comitear, **no**
  pushear, **no** fusionar: el padre revisa y comitea.

## Tareas
- [ ] ENC04-T1 Carga de entidades desde YAML y búsqueda con spans, sin distinguir
  mayúsculas, con límites de palabra y con la variante más larga primero. Aceptación:
  "según GAD3" encuentra GAD3; "PP" no se detecta dentro de "APP"; las tildes no
  impiden encontrar "Simple Lógica". Riesgo RDD: bajo
- [ ] ENC04-T2 Spans de estimación de voto: formación + número/porcentaje/"escaños" en
  la misma frase. Aceptación: "El Partido Azul obtendría un 32 %" produce un span;
  "El Partido Azul ganó las elecciones" no. Riesgo RDD: medio
- [ ] ENC04-T3 Troceado de frases con posiciones correctas sobre el texto original
  (verificable recortando `text[start:end]`). Aceptación: el recorte de cada frase
  reproduce la frase. Riesgo RDD: medio
- [ ] ENC04-T4 Pistas por ítem y `candidates_for` / `all_candidates`. Aceptación: los
  ítems P0 (muestra, margen, fechas de campo, entidad) encuentran su frase en una
  noticia realista; un ítem sin pistas devuelve lista vacía. Riesgo RDD: medio

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|

## Revisión nativa (RDD)
| Tarea | Nivel | Resultado |
|---|---|---|

## Progreso
- Delegado al worker con este documento como especificación.

## Siguiente paso
Verificar la entrega del worker, comitear, fusionar a `dev` y comprobar CI.

## Contexto de arranque para el worker

Repositorio: `C:/Users/alber/orca/Lector-de-encuestas`. Rama actual:
`feature/enc-04-candidatos`.

Ficheros que ya existen y hay que respetar:
- `server/src/ficha_tecnica/extractor/{__init__,numbers,dates,metrics}.py`
- `config/checklist.v1.yaml` (ids y capas de los ítems)
- `config/pollsters.yaml` y `config/parties.yaml` (estructura: `version`, lista con
  `name` y `variants`)

Convenciones del repositorio: Python 3.14, tipado estricto (pyright en modo standard),
líneas de 100 caracteres, comentarios y docstrings en inglés, mensajes de commit en
inglés, Conventional Commits. Los tests van en `server/tests/test_extractor_*.py`.
