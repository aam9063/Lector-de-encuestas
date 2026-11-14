/**
 * Types mirroring the backend contract (section 8 of the design doc).
 * The backend sanitized the finding messages: the web never rewrites them.
 */

export type ItemStatus = "present" | "absent" | "refers_external" | "review";
export type Layer = "formal" | "methodological" | "auxiliary";
export type Severity = "high" | "medium" | "low" | "note";
export type FindingSource = "code" | "clef" | "both" | "computation";
export type Semaphore = "red" | "amber" | "green" | "grey";
export type VerificationVerdict = "wrong" | "right" | "unsure";

export interface Span {
  start: number;
  end: number;
}

export interface Finding {
  item_id: string;
  layer: Layer;
  status: ItemStatus;
  severity: Severity;
  source: FindingSource;
  probability: number | null;
  evidence: Span[];
  /** Already sanitized by the backend: no figures, no party names. Never edited here. */
  message: string;
}

export interface Computation {
  sample_size: number | null;
  declared_margin: number | null;
  theoretical_margin: number | null;
  lead_ratio: number | null;
}

export interface Report {
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

export interface ChecklistItem {
  id: string;
  layer: Layer;
  weight: "high" | "medium" | "low";
  base: string;
}

export interface Checklist {
  version: number;
  items: ChecklistItem[];
}
