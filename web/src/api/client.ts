import type { Checklist, Report } from "./types";

const BASE = "/v1";

/** Error raised for any request that does not succeed. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function errorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim().length > 0) {
        return detail;
      }
    }
  } catch {
    // Fall through to the generic message below.
  }
  if (response.status === 413) return "El texto es demasiado largo.";
  return `El servidor ha respondido con el código ${response.status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("No se ha podido contactar con el servidor de análisis.", 0);
  }
  if (!response.ok) {
    throw new ApiError(await errorDetail(response), response.status);
  }
  return (await response.json()) as T;
}

/** POST /v1/analyses with the pasted text. */
export function analyzeText(text: string): Promise<Report> {
  return request<Report>("/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

/** GET /v1/checklist, used for human-readable item names (never hardcoded here). */
export function getChecklist(): Promise<Checklist> {
  return request<Checklist>("/checklist");
}
