import type { ChecklistItem, FindingSource, ItemStatus, Semaphore } from "../api/types";

const numberFormatEs = new Intl.NumberFormat("es-ES", {
  maximumFractionDigits: 1,
  minimumFractionDigits: 0,
});

const integerFormatEs = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });

const percentFormatEs = new Intl.NumberFormat("es-ES", {
  style: "percent",
  maximumFractionDigits: 0,
});

/** Formats a decimal figure the Spanish way: 2.8 -> "2,8". */
export function formatDecimal(value: number): string {
  return numberFormatEs.format(value);
}

/** Formats a percentage probability (0..1) the Spanish way: 0.96 -> "96 %". */
export function formatPercent(value: number): string {
  return percentFormatEs.format(value);
}

/** Formats a count the Spanish way, with dot thousands: 1200 -> "1.200". */
export function formatCount(value: number): string {
  return integerFormatEs.format(value);
}

/** Capitalized, spaced fallback for any identifier the checklist does not explain. */
export function humanizeId(id: string): string {
  const spaced = id.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * Spanish display names for checklist items, keyed by the id suffix (everything after
 * the group prefix). The checklist itself, with its items and weights, always comes
 * from GET /v1/checklist and is never duplicated here; this map only translates the
 * vocabulary so the sheet can show Spanish names to the reader. Unknown suffixes fall
 * back to the humanized id.
 */
const ITEM_SUFFIX_NAMES: Record<string, string> = {
  entity: "Entidad que realizó la encuesta",
  entity_address: "Domicilio o sede del encuestador",
  client: "Quién encargó o financió la encuesta",
  sample_size: "Tamaño de la muestra",
  margin: "Margen de error",
  confidence: "Nivel de confianza del margen",
  universe: "Universo y ámbito de la encuesta",
  sampling_system: "Sistema de muestreo",
  selection_procedure: "Selección de las personas encuestadas",
  mode: "Modo de las entrevistas",
  fieldwork_dates: "Fechas del trabajo de campo",
  question_text: "Redacción exacta de las preguntas",
  nonresponse: "No respuesta por pregunta",
  weighting: "Ponderación de los datos",
  external_sheet: "Ficha técnica publicada en otro sitio",
};

/**
 * Readable Spanish name for one checklist item. When the checklist is unavailable the
 * id itself is humanized, so new or missing items never break the sheet.
 */
export function itemName(item: ChecklistItem | undefined, itemId: string): string {
  if (item === undefined) return humanizeId(itemId);
  const suffix = itemId.replace(/^[a-z]+_/, "");
  return ITEM_SUFFIX_NAMES[suffix] ?? humanizeId(itemId);
}

export interface StatusStyle {
  icon: string;
  label: string;
  badgeClass: string;
}

/** Status is conveyed by icon AND text; colour is never the only signal. */
export const STATUS_STYLES: Record<ItemStatus, StatusStyle> = {
  present: {
    icon: "✓",
    label: "Aporta el dato",
    badgeClass: "bg-green-100 text-green-900 ring-1 ring-green-300",
  },
  absent: {
    icon: "✕",
    label: "Falta el dato",
    badgeClass: "bg-red-100 text-red-900 ring-1 ring-red-300",
  },
  refers_external: {
    icon: "→",
    label: "Remite a otra ficha",
    badgeClass: "bg-sky-100 text-sky-900 ring-1 ring-sky-300",
  },
  review: {
    icon: "?",
    label: "Revisar a mano",
    badgeClass: "bg-amber-100 text-amber-900 ring-1 ring-amber-300",
  },
};

export interface SemaphoreStyle {
  icon: string;
  title: string;
  description: string;
  boxClass: string;
}

export const SEMAPHORE_STYLES: Record<Semaphore, SemaphoreStyle> = {
  red: {
    icon: "✕",
    title: "Faltan datos obligatorios",
    description:
      "A la noticia le faltan datos que la ficha técnica debe recoger. Léela con cautela y mira qué falta abajo.",
    boxClass: "bg-red-700 text-white",
  },
  amber: {
    icon: "△",
    title: "Ficha con avisos",
    description:
      "Hay datos que faltan o puntos que no están claros. Revisa el detalle antes de publicar.",
    boxClass: "bg-amber-400 text-amber-950",
  },
  green: {
    icon: "✓",
    title: "Ficha completa",
    description: "La noticia recoge los datos de la ficha técnica.",
    boxClass: "bg-green-700 text-white",
  },
  grey: {
    icon: "?",
    title: "No parece una encuesta",
    description:
      "El texto no se parece a una encuesta, así que la ficha técnica no aplica. No hay hallazgos que leer.",
    boxClass: "bg-slate-400 text-slate-950",
  },
};

const SOURCE_LABELS: Record<FindingSource, string> = {
  code: "código",
  clef: "Clef",
  both: "código y Clef",
  computation: "cálculo",
};

export function sourceLabel(source: FindingSource): string {
  return SOURCE_LABELS[source];
}

const POLL_TYPE_LABELS: Record<string, string> = {
  voting_intention_estimate: "Estimación de intención de voto",
  direct_voting_intention: "Pregunta directa de intención de voto",
  leader_ratings: "Valoración de líderes",
  issue_opinion: "Opinión sobre asuntos",
  self_selected_online_poll: "Votación abierta online con muestra autoseleccionada",
  poll_of_polls_or_model: "Agregación de encuestas o modelo",
  not_a_poll: "No parece una encuesta",
};

export function pollTypeLabel(pollType: string): string {
  return POLL_TYPE_LABELS[pollType] ?? humanizeId(pollType);
}
