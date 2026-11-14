# ENC-14 + ENC-15: Interfaz web con ficha, evidencia y "revisar a mano"

Una sola unidad: son dos pantallas del mismo flujo y comparten estado.

## Especificación (literal)

Backlog de la ficha técnica (sección 14):

| Id | Tarea | Criterio de aceptación | Riesgo RDD |
|---|---|---|---|
| ENC-14 | UI: pegar texto y ficha con semáforo | Flujo completo con el ejemplo simulado | Bajo |
| ENC-15 | UI: evidencia, probabilidades y "Revisar" | Resaltado de frases candidatas | Bajo |

Sección 10, pantallas:

| Pantalla | Contenido |
|---|---|
| Inicio | Caja para pegar el texto, botón de ejemplo ("simulación" etiquetada) y aviso de que no es asesoramiento jurídico |
| Ficha | Semáforo grande, dos bloques (formal y metodológica) con filas por ítem: icono de estado, nombre, motivo en una línea |
| Evidencia | Al abrir una fila se resaltan en el texto las frases candidatas. Un cajón enseña las probabilidades de Clef y su versión de cuestionario |
| "Revisar a mano" | Estado visible y explicado: "no estamos seguros, mira esta frase" |
| Veda | Pantalla de aviso con la fecha y la razón, sin hallazgos |

> Principios: **nunca** un número único de "calidad de la encuesta", nunca el nombre de una
> formación en un hallazgo, y siempre el aviso de que la valoración jurídica es de la JEC.

Sección 17 (guion de demo) marca el recorrido: pegar → ficha con semáforo → abrir un ítem y
ver la frase candidata y las probabilidades → un ítem en "Revisar a mano" → la misma noticia
con ficha completa en verde → paráfrasis M14 que no dispara falsas acusaciones → veda.

## Objetivo
Que una persona pegue una noticia y vea, en un par de segundos, qué información falta y
dónde mirar, sin leer nada más.

## Problema y motivo
Toda la maquinaria del backend no vale nada si el jurado no puede verla. Y la interfaz tiene
una obligación propia: no puede insinuar más de lo que el motor sabe.

## Alcance
- Dentro: `web/` completo. Pantalla de entrada, ficha con semáforo y bloques, evidencia
  resaltada sobre el texto pegado, cajón de probabilidades, estado "revisar a mano", aviso de
  veda, aviso legal siempre visible, y un botón de ejemplo con noticia simulada.
- Fuera: panel interno de evaluación (ENC-17), modo URL (ENC-13), resultados reales de la
  evaluación.

## Contrato de la API que hay que consumir

`POST /v1/analyses` con `{"text": "..."}` → 200 con:

```ts
type ItemStatus = "present" | "absent" | "refers_external" | "review";
type Layer = "formal" | "methodological" | "auxiliary";
type Severity = "high" | "medium" | "low" | "note";
type Semaphore = "red" | "amber" | "green" | "grey";

interface Finding {
  item_id: string;          // "a_sample_size", ...
  layer: Layer;
  status: ItemStatus;
  severity: Severity;
  source: "code" | "clef" | "both" | "computation";
  probability: number | null;
  evidence: { start: number; end: number }[];  // índices sobre el texto pegado
  message: string;          // ya viene saneado y sin cifras
}

interface Computation {
  sample_size: number | null;
  declared_margin: number | null;
  theoretical_margin: number | null;
  lead_ratio: number | null;   // r = ventaja / margen
}

interface Report {
  id: string;
  created_at: string;
  text_hash: string;
  checklist_version: number;
  questionnaire_version: number;
  provider: "nan" | "mock";
  poll_type: string;
  poll_type_probs: Record<string, number>;
  semaphore: Semaphore;
  status: "ok" | "veda";
  findings: Finding[];
  computation: Computation | null;
  disclaimer: string;
  latency_ms: number;
}
```

Otros endpoints: `GET /v1/analyses/{id}` (misma forma), `GET /v1/checklist`
(`{version, items: [{id, layer, weight, base, question}]}`), `GET /v1/config`
(`{checklist_version, questionnaire_version, policy_version, provider, veda:{mode, active,
start, end}}`), `POST /v1/analyses/{id}/feedback` con `{item_id, verdict}` donde `verdict` es
`"wrong" | "right" | "unsure"`, `GET /v1/health`.

El proxy `/v1` ya está configurado hacia `http://localhost:8000` en `web/vite.config.ts`.

## Restricciones
- **Nunca** un número único de calidad, ni una puntuación agregada, ni "esta encuesta es
  buena/mala".
- **Nunca** el nombre de una formación en un hallazgo. Los mensajes vienen del backend ya
  saneados: no los reescribas ni los completes.
- El aviso "no es asesoramiento jurídico; la valoración es de la Junta Electoral Central"
  debe estar visible en la ficha, no escondido en un pie.
- El texto pegado se escapa siempre (React lo hace por defecto; no uses `dangerouslySetInnerHTML`).
- El resaltado de evidencia usa `text.slice(start, end)` sobre el texto original del usuario.
- Si `status === "veda"`, no se muestran hallazgos: solo el aviso con las fechas.
- Si `semaphore === "grey"` y `status === "ok"`, explicar que no parece una encuesta.
- Español en toda la copia visible. Tailwind v4, sin librerías de UI nuevas.
- Accesibilidad: los estados no dependen solo del color (icono + texto), contraste razonable,
  navegable con teclado.

## Configuración de pruebas
- Modo TDD: **excepción documentada**, la que fija la sección 15.3 de la ficha para `web`:
  no hay runner de tests de UI y añadirlo no está en esta tarea.
- Runner exacto: `pnpm --dir web lint && pnpm --dir web typecheck && pnpm --dir web build`
- Comprobación funcional: arrancar el backend (`uv run uvicorn ficha_tecnica.api.app:app`),
  `pnpm --dir web dev` y recorrer el flujo de la sección 17 con la noticia de ejemplo.

## Entrega
- Estrategia: ask-on-risk
- Líneas: ~500
- Slices: rama `feature/enc-14-15-web` (ya creada). **No** comitear, **no** pushear.

## Tareas
- [ ] ENC14-T1 Cliente tipado de la API y tipos del informe. Aceptación: `tsc` en verde y
  ningún `any` en el cliente.
- [ ] ENC14-T2 Pantalla de entrada: textarea, botón de ejemplo claramente marcado como
  simulación, aviso legal, estados de carga y error legibles.
- [ ] ENC14-T3 Ficha: semáforo grande con icono y texto, dos bloques separados (formal y
  metodológica), fila por ítem con icono de estado, nombre legible y motivo en una línea.
- [ ] ENC14-T4 Bloque de cálculos: muestra, margen declarado, margen teórico y `r` con su
  lectura (dentro del margen / no concluyente / probablemente real). Sin nombrar partidos.
- [ ] ENC15-T1 Evidencia: al abrir una fila, resaltar sus frases sobre el texto pegado y
  mostrar el cajón con las probabilidades y la versión del cuestionario.
- [ ] ENC15-T2 "Revisar a mano" visible y explicado; también la veda y el caso "no es una
  encuesta".
- [ ] ENC15-T3 Nombres legibles de los ítems (a partir de `GET /v1/checklist`) sin duplicar
  la lista en el código.

## Evidencia de verificación
| Tarea | Prueba | Resultado | Commit |
|---|---|---|---|

## Progreso
- Delegado al worker.

## Siguiente paso
Revisión del padre, comprobación funcional del flujo de la sección 17, commit y merge.

## Contexto de arranque para el worker

Repositorio: `C:/Users/alber/orca/Lector-de-encuestas`. Rama ya activa:
`feature/enc-14-15-web`.

Estado actual de `web/`: Vite + React 19 + TypeScript + Tailwind v4, con `App.tsx` como
placeholder (textarea y botón deshabilitado). Scripts: `dev`, `build` (`tsc -b && vite
build`), `lint` (oxlint), `typecheck` (`tsc -b`), `generate:api` (openapi-typescript).

Noticias de ejemplo para el botón: usa una noticia **simulada** inventada, con entidades
ficticias ("Demoscopia Ficticia S.L."), empezando por "SIMULACIÓN" y con datos completos,
más una segunda versión a la que le falte el tamaño de muestra y el margen, para enseñar los
dos semáforos en la demo.

Convenciones: TypeScript estricto, componentes funcionales, sin dependencias nuevas,
identificadores y comentarios en inglés, copia visible en español.
