# Ficha Técnica — informe de desarrollo

Documento vivo. Se actualiza al cerrar cada unidad de trabajo, y la sección de errores se
escribe **cuando el error ocurre**, no al final: un registro reconstruido de memoria pierde
justo lo que interesa, que es el razonamiento que falló.

- Repositorio: `github.com/aam9063/Lector-de-encuestas`
- Ficha de referencia: [`lector-de-encuestas.md`](./lector-de-encuestas.md)
- Especificaciones por tarea: [`odd/tasks/`](./odd/tasks)
- Estado: backend completo (ENC-01 a ENC-12), interfaz (ENC-14/15) y evaluación (ENC-16/17).
  Faltan ENC-13 (modo URL) y ENC-18/19 (contrato de cola, README y guion).
- Compuerta actual: **484 tests**, `ruff` y `pyright` en verde, CI en verde sobre `dev`.

---

## 1. Objetivo

Una aplicación que recibe el texto de una noticia sobre una encuesta y devuelve una **ficha
de lectura**: qué información necesaria para interpretar esa encuesta aparece, cuál falta y
dónde está la que sí aparece.

Tres límites definen el producto, y son límites, no funcionalidades pendientes:

1. **No juzga si la encuesta es verdadera** ni a favor de quién juega. Describe la
   información que la noticia da.
2. **No reproduce cifras de estimación de voto** ni nombra formaciones en sus hallazgos. Es
   una regla dura, siempre activa.
3. **No aplica la ley.** Marca con la etiqueta "formal" los ítems que coinciden con el
   artículo 69 de la LOREG y repite en cada informe que la valoración jurídica corresponde a
   la Junta Electoral Central.

La frase que resume el criterio: *prefiere decir "revisá esto a mano" antes que acusar en
falso*. Esa preferencia está implementada como asimetría de umbrales, no como intención.

---

## 2. Principios que gobiernan el código

| Principio | Cómo se traduce en código | Dónde se verifica |
|---|---|---|
| Si se puede decidir con código, se decide con código | Aritmética de márgenes, saneado y veda son módulos deterministas sin acceso al modelo | `policy/calculator.py` no importa el cliente de Clef; hay un test que lee su propio fuente para comprobarlo |
| El modelo solo interpreta | Clef responde preguntas de sí/no sobre un texto acotado; nunca calcula ni decide umbrales | `extractor/digest.py` acota el estado; `policy/states.py` decide |
| Acusar exige mucha más certeza que confirmar | Con candidato del código, un ítem **nunca** puede quedar `absent`; ausente exige ausencia de candidato *y* p ≤ 0,10 | `tests/test_policy_states.py`, incluido el caso p = 0,0 |
| La duda no escala a acusación | Zona gris → segunda lectura enfocada → si persiste, `review` | `tests/test_second_reading.py` |
| No se guarda el texto de la noticia | Solo un hash SHA-256; la base se inspecciona directamente en los tests | `tests/test_api_analyses.py` vuelca todas las tablas y busca fragmentos |
| Falla cerrado | Ante ambigüedad, enmascara o se abstiene | `tests/test_sanitizer_adversarial.py` |

---

## 3. Arquitectura implementada

```
server/src/ficha_tecnica/
├── schema/         modelos Pydantic del informe, checklist tipada, cuestionario tipado
├── extractor/      parser español, entidades, candidatos por ítem, digests, normalización
├── clef_client/    DecisionProvider: adaptadores nan y mock, semáforo de 2, errores
├── policy/         umbrales, estados, semáforo, calculadora M4/M5, veda
├── sanitizer/      enmascarado de cifras + detector independiente
├── evaluation/     corpus sintético, baselines, métricas, tabla y gráfica
└── api/            pipeline de análisis, persistencia sin texto, rutas /v1
web/                React 19 + Vite + Tailwind v4: pegar, ficha, evidencia
config/             checklist, cuestionario, política, veda, listas curadas
```

| Módulo | Responsabilidad | Decisión de diseño y motivo |
|---|---|---|
| `extractor/numbers.py` | `1.200` = mil doscientos, `2,8` = dos coma ocho | Reglas estrictas y `Decimal`: leer `1.200` como 1,2 convierte una muestra de 1.200 personas en 1,2 y produce un hallazgo aritmético falso |
| `extractor/dates.py` | "del 3 al 9 de noviembre" | Ventana semiabierta y cambio de año; el rango invertido devuelve `None` |
| `extractor/metrics.py` | Muestra, margen y confianza | Cada cifra exige una pista cercana: una cuota de voto nunca se lee como margen |
| `extractor/candidates.py` | Frases candidatas por ítem, con posiciones | Pistas sin tilde sobre texto plegado 1:1, para que un texto sin tildes encuentre lo mismo |
| `extractor/normalize.py` | Limpia artefactos de pegado | Sustituye por espacios, nunca borra: si cambia la longitud, se desplazan todos los spans |
| `clef_client/` | Una interfaz, dos adaptadores | Semáforo de 2 por instancia y reintento inmediato en 429; el proveedor se construye una vez por app |
| `policy/states.py` | Tabla 7.2 celda por celda | La asimetría es el producto |
| `policy/calculator.py` | M4 y M5 | Todo en `Decimal`; un redondeo mueve un hallazgo de lado a lado de un umbral |
| `sanitizer/` | Enmascarado + detector | El detector se construye **distinto** a propósito (ver §7) |
| `api/store.py` | SQLite sin texto | La promesa se verifica volcando la base, no leyendo el código |

---

## 4. Estado por tarea

| Id | Tarea | Estado | Evidencia |
|---|---|---|---|
| ENC-01 | Estructura, CI, githooks, plantillas | hecho | merge `4ed5355` |
| ENC-02 | `DecisionProvider` nan/mock y contrato real | hecho | merge `b6d7f4e`, 3 fixtures capturadas |
| ENC-03 | Parser español y métricas con pistas | hecho | merge `7cb8581`, 66 tests |
| ENC-04 | Entidades, estimaciones y candidatos | hecho | merge `d25f148` |
| ENC-05 | Digest acotado A/B/C | hecho | merge `fa1eb55` |
| ENC-06 | Cuestionario v1 tipado con snapshot | hecho | merge `fa1eb55` |
| ENC-07 | Política asimétrica y semáforo | hecho | merge `73b7fbb`, tabla 7.2 completa |
| ENC-08 | Calculadora M4/M5 | hecho | merge `4e3fb90`, tabla de `n` fila por fila |
| ENC-09 | Saneador y detector independiente | hecho | merge `ef2e837`, 12 formulaciones adversarias |
| ENC-10 | Veda por fecha | hecho | merge `faa6426`, bordes por los dos lados |
| ENC-11 | API `/v1/analyses` sin guardar texto | hecho | merge `a9924f4` |
| ENC-12 | Segunda lectura enfocada | hecho | merge `ad0add4` |
| ENC-14/15 | Interfaz con ficha y evidencia | hecho | merge `bcaf9cd`, recorrida en navegador |
| ENC-16/17 | Corpus sintético y harness B0–B4 | hecho, con hallazgo abierto (§8) | rama `feature/enc-16-17-eval` |
| ENC-13 | Modo URL con fetch seguro (SSRF) | pendiente | — |
| ENC-18 | Contrato del cliente real y cola de 2 | parcial: cubierto por ENC-02, falta simulación multiusuario | — |
| ENC-19 | README, guion y vídeo | pendiente | — |

---

## 5. Cómo se verifica (y por qué así)

Cada unidad pasa por cuatro capas, y cada una atrapa una clase de error distinta:

| Capa | Qué atrapa | Ejemplo real |
|---|---|---|
| Test-first (RED observado) | Que la implementación no haga lo que se cree | El RED de ENC-08 destapó 4 campos que faltaban en la configuración |
| Suite + lint + tipos | Regresiones y contratos | `pyright` obligó a tipar `source`/`severity` como literales en vez de `str` |
| Prueba en vivo con el modelo real | Que el sistema sea inútil con entradas reales | Tres bugs de §7 que ninguna de las capas anteriores vio |
| Navegador real | Que la interfaz no renderice | El aviso legal duplicado |

La lección que costó más: **las tres primeras capas pueden estar verdes y el producto roto**.
La app usaba el proveedor mock en todas las fichas y los 393 tests no lo detectaban, porque
los tests también usaban el mock.

Entregas delegadas: se reproduce la compuerta del worker y **además** se escribe un test de
aceptación propio, sobre comportamiento y no sobre implementación. En dos de tres entregas
ese test encontró un agujero real (ver E-05 y E-06).

---

## 6. Registro de errores

### 6.1 Resumen

| Id | Error | Detectado por | Gravedad |
|---|---|---|---|
| E-01 | Commit directo a `dev` | Inspección de rama antes de comitear | media |
| E-02 | Código antes que los tests | Al escribir el test | baja |
| E-03 | Documento de feature escrito al final | Autorrevisión contra ODD | baja |
| E-04 | `.env.example` bloqueado por la guarda | La herramienta se negó a escribirlo | baja |
| E-05 | `a_sample_size` no detectaba "1.200 entrevistas" | Test de aceptación propio | **alta** |
| E-06 | Pistas con tilde fallaban en texto sin tildes | Test de aceptación propio | **alta** |
| E-07 | Heredoc convirtió `\b` en carácter de control | La suite falló de inmediato | media |
| E-08 | `KeyError` latente si la checklist crece | Lectura de código | media |
| E-09 | La app usaba siempre el proveedor mock | Prueba en vivo | **crítica** |
| E-10 | "SIMULACIÓN." tomado como titular → semáforo gris | Prueba en vivo | **crítica** |
| E-11 | El troceador cortaba dentro de "S.L." | Prueba en vivo, reporte del usuario | **crítica** |
| E-12 | Cerca markdown en línea propia ignorada a medias | Prueba en vivo | alta |
| E-13 | Cerca pegada al texto borraba la noticia entera | Prueba en vivo | **crítica** |
| E-14 | Verificar una sola vez cerca de un umbral | El usuario reportó que seguía fallando | **alta** |
| E-15 | Test que dependía del `.env` del desarrollador | El test falló en local con clave real | media |
| E-16 | El semáforo no recibía `poll_type` | Test de `not_a_poll` | media |
| E-17 | `PolicyConfig` sin campos que la calculadora usaba | RED de los tests | baja |
| E-18 | `ruff --fix` borró imports que aún no tenían uso | `NameError` en runtime | media |
| E-19 | Modelos Pydantic construidos con argumentos posicionales | `TypeError` | baja |
| E-20 | Aviso legal duplicado en la ficha | Navegador real | media |
| E-21 | CI: `pnpm/action-setup` sin `package_json_file` | CI en rojo | media |
| E-22 | Corpus de evaluación sin entidades reconocibles → métrica vacua | Verificación propia del corpus | **alta** |
| E-23 | Recall de omisiones del 6,67 % | Medición real | **abierto** |

### 6.2 Fichas

**E-01 · Commit directo a `dev`**
*Síntoma:* el commit de ENC-03 quedó en `dev` sin rama. *Causa:* no comprobé la rama antes de
comitear; venía de fusionar y seguí escribiendo. *Arreglo:* `git switch -c feature/...`,
`git branch -f dev <hash previo>`, merge `--no-ff`. Sin pérdida de trabajo porque el commit
estaba solo en local. *Prevención:* desde entonces la rama se verifica antes de cada commit;
el flujo queda escrito en el documento de feature.

**E-05 · `a_sample_size` no detectaba "1.200 entrevistas"**
*Síntoma:* ninguno. El worker entregó 64 tests verdes. *Diagnóstico:* escribí un test de
aceptación propio con una noticia completa; el ítem P0 de gravedad alta devolvía lista vacía.
*Causa raíz:* la tabla de pistas tenía `entrevistad[ao]s` pero no `entrevistas`, el patrón
canónico de la propia ficha técnica. *Arreglo:* añadir el plural. *Prevención:* test de
aceptación sobre prosa realista, no sobre reglas sueltas.

**E-06 · Pistas con tilde**
*Síntoma:* un texto sin tildes no encontraba **ninguna** evidencia. *Causa:* las pistas
llevaban tilde y el corpus de evaluación incluye un estilo "hilo de red social", que las
pierde. *Arreglo:* pistas escritas sin tilde, buscadas sobre una copia plegada 1:1 del texto.
Al ser 1:1, las posiciones siguen siendo válidas sobre el original. *Prevención:* test que
compara el mismo texto con y sin tildes.

**E-09 · La app usaba siempre el proveedor mock**
*Síntoma:* las fichas se veían razonables, pero 11 de 15 ítems quedaban en "revisar".
*Causa:* `create_app` construía `MockProvider()` en duro. *Por qué no lo vieron los tests:* los
tests también usan el mock, así que la suite era coherente consigo misma. *Arreglo:*
`build_provider()` elige `nan` si hay clave, `mock` si no, y el informe **dice cuál se usó**.
*Prevención:* test de que el nombre reportado coincide con el proveedor real, para que una
ficha construida con respuestas planas no pueda pasar por lectura real.

**E-10 · "SIMULACIÓN." como titular**
*Síntoma:* una noticia que era claramente una encuesta salía con semáforo **gris** ("no es
una encuesta"). *Diagnóstico:* llamada real con tres variantes de apertura; solo fallaba con
el marcador. *Causa raíz:* el digest tomaba la primera frase como titular, y "SIMULACIÓN"
sola le dice al modelo "esto no es una encuesta real" (p = 0,68–0,81). *Arreglo:* el titular
descarta etiquetas cortas y recorta a 200 caracteres. *Por qué importa más allá de la demo:*
todo el corpus de evaluación exige ese marcador, así que el bug habría hecho que la
evaluación entera diera "sin hallazgos" y pareciera que el sistema funciona.

**E-11 · El troceador cortaba dentro de "S.L."**
*Síntoma:* el usuario reportó que el texto seguía en gris después del arreglo de E-10.
*Diagnóstico:* imprimí el estado que recibe el modelo: titular terminado en "Ficticia S." y
lede empezando por "L. , cuya sede…". *Causa raíz:* el troceador de frases corta en todo
punto que no vaya seguido de dígito, y las abreviaturas españolas llevan punto. El modelo no
se equivocaba: leía basura. *Arreglo:* enmascarado de abreviaturas conocidas sustituyendo el
punto por un carácter no terminador, con la longitud intacta. *Prevención:* 21 tests nuevos,
incluido que los spans sigan recortando el texto original.

**E-13 · Una cerca pegada borraba la noticia entera**
*Síntoma:* ` ```texto...``` ` en una sola línea producía semáforo gris con p = 0,9.
*Causa raíz:* el patrón de cercas iba **por línea** (`(?m)^\s*```[^\n]*$`), así que en un texto
de una línea reemplazaba 341 caracteres por espacios: el modelo recibía un estado vacío.
*Arreglo:* el patrón va por **marcador** (` ```(?:markdown|md|...)? `), pegada o no.
*Prevención:* test de regresión específico.

**E-14 · Verificar una sola vez cerca de un umbral**
*Síntoma:* la primera corrección se dio por buena y el usuario seguía viendo gris.
*Causa raíz:* corrí el texto **una vez**, sin cercas, obtuve verde y cerré el caso. El
resultado estaba a 0,08 de un umbral; una sola muestra no prueba nada. *Arreglo:* a partir de
ahí, cuatro formas de pegado × tres corridas cada una antes de dar algo por cerrado.
*Prevención de método:* cerca de un umbral se repite; y se prueba la entrada como la produce
el usuario, no como la produce el test.

**E-22 · El corpus no podía disparar el saneador ni M5**
*Síntoma:* los tests del worker estaban verdes y la métrica "fugas del saneador" daba 0.
*Diagnóstico:* en vez de leer los tests, conté sobre el corpus: **0 de 280** casos producían
un span de estimación de voto y **0 de 280** activaban el saneador. *Causa raíz:* el corpus
usa formaciones ficticias que no estaban en `config/parties.yaml`, así que ni el extractor de
estimaciones ni el saneador las veían. La métrica de cero fugas era **vacua**: el detector no
encontraba nada porque no había nada que encontrar. *Arreglo:* las formaciones y casas
simuladas se registran en las listas curadas y ambos lados —saneador y detector
independiente— las cargan. Resultado: **280/280** casos ejercitan estimaciones, entidades y
saneado, con **0 fugas** reales. *Prevención:* el test que antes exigía que el corpus no
tuviera estimaciones ahora exige lo contrario y se ancla con `masked_somewhere > 0`, para que
no pueda volver a pasar en silencio.

---

## 7. Decisiones discutidas e interpretaciones de la ficha

| Tema | Qué dice la ficha | Qué hicimos y por qué |
|---|---|---|
| Detector del saneador | "un detector independiente de formación + porcentaje" | Se construyó con **otro algoritmo**: ventana por terminadores, su propia gramática de cifras y su propio matcher. Un detector que comparte el punto ciego del saneador reporta cero fugas mientras la app filtra. Sus controles positivos son lo que hace que el cero signifique algo |
| M6, M7, M9 | Aparecen como disparadores ámbar, sin definición | Se aceptan como identificadores y se dejan **inertes**. Inventar su significado habría sido peor que dejar el hueco visible |
| M12, M13 | Flags del grupo B sin color asignado | Se calculan y no colorean el semáforo; hay un test que lo fija, para que el día que se decida lo contrario el cambio sea visible |
| B1 y B2 | Jueces LLM de NaN con y sin razonamiento | Se reportan como **`unavailable`** con una razón. No hay acceso a modelos de chat configurado. Simular su latencia o su precisión habría fabricado la conclusión de la demo |
| Generación del corpus | "40 artículos base generados con un modelo de NaN" | Generación **determinista desde plantillas**. Reproducible, gratis, versionable y revisable. Queda documentado como desviación consciente |
| Veda | Ventana del 24 al 29 de noviembre, marcada `[VERIFICAR]` | Implementada como configuración semiabierta, con `VEDA_NOW` para simular. Sigue pendiente confirmarlo con la JEC |
| "Ciudadanos" | Nombre de partido y sustantivo común | Se enmascara igual. Fallar cerrado: una cifra perdida cuesta una frase, una cifra publicada cuesta el proyecto |
| Cifra en la frase siguiente | El saneado es "cualquier frase" | Límite declarado: no se enmascara. Las salidas son plantillas fijas sin cifras y la aritmética se expresa con razones |

---

## 8. Medición actual

Primera corrida real contra Clef, 12 casos, baseline B4 (sistema completo):

| Métrica | Valor | Objetivo (ficha) | Lectura |
|---|---|---|---|
| Falsa acusación | **0,00 %** (0/165) | ≤ 2 % | Cumple con margen |
| Recall de omisiones | **6,67 %** | ≥ 85 % | **Muy por debajo** |
| Ítems en revisar | 0,00 % | ≤ 20 % | Cumple, pero por el motivo equivocado |
| Exactitud M4 | 1,000 | 100 % | Cumple |
| Exactitud M5 | 1,000 | 100 % | Cumple |
| Calibración | 0,204 | informativo | Poca confianza en las probabilidades |
| Estabilidad | 1,000 | Clef ≈ 100 % | Cumple |
| Latencia | p50 461 ms / p95 867 ms | frente a B1/B2 | Rápido, sin comparación disponible |
| Fugas del saneador | **0** | 0 | Cumple, y ahora de forma no vacua |

**Hallazgo abierto (E-23).** El sistema casi no acusa en falso, pero también casi no detecta
omisiones: predice "presente" donde el gold dice "ausente". Con 0 % de ítems en revisión y
6,67 % de recall, la asimetría está funcionando tan bien que la herramienta pierde su
utilidad. Hipótesis a comprobar, en orden:

1. El digest A incluye frases técnicas que mencionan el ítem por otra vía, así que el modelo
   responde "presente" con razón aunque el dato concreto se haya borrado.
2. Las preguntas del cuestionario son demasiado indulgentes ("¿el texto dice cuántas personas
   fueron entrevistadas?" admite una respuesta afirmativa por proximidad).
3. Las mutaciones de deleción no son limpias: quitan la frase pero dejan pistas.

Sin resolver esto, la gráfica de la demo contaría media verdad. Se reporta tal cual, como
pide la ficha: *si los resultados no lo respaldan, se cuentan como son*.

---

## 9. Riesgos abiertos

| Riesgo | Estado | Mitigación actual |
|---|---|---|
| Recall real desconocido | Abierto (E-23) | Medición reproducible con el harness |
| `config/pollsters.yaml` a medio curar | Abierto | Clef cubre lo que la lista no conoce; evidencia mostrada más pobre |
| Ventana de veda sin confirmar con la JEC | Abierto (`[VERIFICAR]`) | Diseño conservador y configurable |
| Modo URL con `fetch` seguro | No implementado | La API responde 501 con un mensaje explícito |
| Límite por IP y tamaño | Parcial: solo tamaño | Falta ENC-18 |
| B1/B2 sin medir | Bloqueado por acceso a modelos de chat | Se reporta como no disponible |

---

## 10. Bitácora

| Fecha | Hecho | Compuerta |
|---|---|---|
| Arranque | Bootstrap, ENC-01: estructura, CI, githooks | 8 tests |
| Día 1 | ENC-02 contrato real de Clef capturado con 3 fixtures | 20 tests |
| Día 1 | ENC-03 parser español estricto | 66 tests |
| Día 1 | ENC-04 entidades, estimaciones y candidatos | 164 tests |
| Día 1 | ENC-05/06 cuestionario tipado y digests acotados | 188 tests |
| Día 1 | ENC-07 política asimétrica y semáforo | 243 tests |
| Día 1 | ENC-08 calculadora M4/M5 — cierra el hito del día 1 | 277 tests |
| Día 2 | ENC-09 saneador y detector independiente | 345 tests |
| Día 2 | ENC-10 veda por fecha | 364 tests |
| Día 2 | ENC-11 API sin guardar texto | 393 tests |
| Día 2 | ENC-12 segunda lectura enfocada | 403 tests |
| Día 2 | ENC-14/15 interfaz, recorrida en navegador | build + typecheck |
| Día 2 | Correcciones E-09 a E-14 encontradas al probar en vivo | 440 tests |
| Día 2 | ENC-16/17 corpus, harness y métricas; E-22 corregido | 484 tests |
