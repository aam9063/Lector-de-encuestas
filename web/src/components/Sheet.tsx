import { useState } from "react";
import type { Checklist, Finding, Report } from "../api/types";
import { FindingRow } from "./FindingRow";
import { itemName, pollTypeLabel, formatCount, formatDecimal, formatPercent, SEMAPHORE_STYLES } from "../lib/labels";

const FORM_TITLE = "Bloque formal";
const FORM_HINT = "Datos que la ley pide publicar junto a la encuesta.";
const METHODOLOGICAL_TITLE = "Bloque metodológico";
const METHODOLOGICAL_HINT = "Buenas prácticas profesionales (AAPOR y guías afines): aviso, no juicio.";
const AUXILIARY_TITLE = "Ficha técnica en otro sitio";
const AUXILIARY_HINT = "Si el texto remite a una ficha publicada en otro sitio, es ahí donde hay que mirar.";

const LAYER_BLOCKS = [
  { layer: "formal", title: FORM_TITLE, hint: FORM_HINT },
  { layer: "methodological", title: METHODOLOGICAL_TITLE, hint: METHODOLOGICAL_HINT },
  { layer: "auxiliary", title: AUXILIARY_TITLE, hint: AUXILIARY_HINT },
] as const;

function groupByLayer(findings: Finding[]): Map<string, Finding[]> {
  const groups = new Map<string, Finding[]>();
  for (const finding of findings) {
    const group = groups.get(finding.layer) ?? [];
    group.push(finding);
    groups.set(finding.layer, group);
  }
  return groups;
}

/** Lead-to-margin reading, mirroring M5 in the design doc. No party is ever named. */
function leadRatioReading(ratio: number | null): string {
  if (ratio === null) {
    return "No se puede calcular: falta el margen declarado o las dos primeras cifras que cita el texto.";
  }
  if (ratio < 1) {
    return "La diferencia está dentro del margen.";
  }
  if (ratio < 2) {
    return "No concluyente según el criterio de AAPOR (se suele pedir entre 1,5 y 2 veces el margen).";
  }
  return "Probablemente real, bajo los supuestos de muestreo aleatorio.";
}

function ComputationRow({ term, value }: { term: string; value: string }) {
  return (
    <div className="flex flex-wrap justify-between gap-2 border-b border-slate-100 py-2 last:border-b-0">
      <dt className="text-sm font-medium text-slate-700">{term}</dt>
      <dd className="text-sm text-slate-900">{value}</dd>
    </div>
  );
}

interface SheetProps {
  report: Report;
  pastedText: string;
  checklist: Checklist | null;
  onBack: () => void;
}

export function Sheet({ report, pastedText, checklist, onBack }: SheetProps) {
  const groups = groupByLayer(report.findings);
  const [openItemId, setOpenItemId] = useState<string | null>(null);
  const toggleItem = (itemId: string) => {
    setOpenItemId((current) => (current === itemId ? null : itemId));
  };
  const openSemaphore = SEMAPHORE_STYLES[report.semaphore];
  const notAPoll = report.semaphore === "grey" && report.status === "ok";
  const computation = report.computation;
  const pollProbs = Object.entries(report.poll_type_probs).sort((a, b) => b[1] - a[1]);

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-slate-900">Lector de fichas técnicas</h1>
        <div
          role="note"
          className="rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-800"
        >
          {report.disclaimer}
        </div>
      </header>

      <section aria-label="Semáforo de la ficha técnica" className={`rounded-2xl p-6 ${openSemaphore.boxClass}`}>
        <p className="text-xs font-semibold uppercase tracking-wide">Semáforo</p>
        <p className="mt-2 flex items-center gap-3">
          <span aria-hidden="true" className="text-4xl font-bold">
            {openSemaphore.icon}
          </span>
          <span className="text-3xl font-bold">{openSemaphore.title}</span>
        </p>
        <p className="mt-2 max-w-prose text-sm">{openSemaphore.description}</p>
      </section>

      {notAPoll ? (
        <p className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
          No parece una encuesta, así que la ficha técnica no aplica a este texto.
        </p>
      ) : null}

      {LAYER_BLOCKS.map((block) => {
        const findings = groups.get(block.layer) ?? [];
        if (findings.length === 0) return null;
        return (
          <section key={block.layer} aria-label={block.title}>
            <h2 className="text-lg font-bold text-slate-900">{block.title}</h2>
            <p className="mb-2 text-sm text-slate-600">{block.hint}</p>
            <ul className="flex flex-col gap-2">
              {findings.map((finding) => (
                <FindingRow
                  key={finding.item_id}
                  finding={finding}
                  name={itemName(
                    checklist?.items.find((item) => item.id === finding.item_id),
                    finding.item_id,
                  )}
                  text={pastedText}
                  expanded={openItemId === finding.item_id}
                  onToggle={toggleItem}
                />
              ))}
            </ul>
          </section>
        );
      })}

      {computation !== null ? (
        <section aria-label="Cálculos sobre las cifras que cita el texto" className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-lg font-bold text-slate-900">Cálculos sobre lo que dice el texto</h2>
          <p className="mb-2 text-sm text-slate-600">
            Aritmética pura sobre las cifras de la noticia. No cita formaciones ni cifra resultados.
          </p>
          <dl>
            <ComputationRow
              term="Muestra"
              value={
                computation.sample_size === null
                  ? "No aparece en el texto"
                  : `${formatCount(computation.sample_size)} personas`
              }
            />
            <ComputationRow
              term="Margen de error declarado"
              value={
                computation.declared_margin === null
                  ? "No aparece en el texto"
                  : `±${formatDecimal(computation.declared_margin)} puntos`
              }
            />
            <ComputationRow
              term="Margen teórico (muestreo aleatorio simple)"
              value={
                computation.theoretical_margin === null
                  ? "No se puede calcular con los datos del texto"
                  : `±${formatDecimal(computation.theoretical_margin)} puntos`
              }
            />
            <ComputationRow
              term="Ventaja frente al margen (r)"
              value={
                computation.lead_ratio === null
                  ? "No se puede calcular"
                  : `${formatDecimal(computation.lead_ratio)} veces el margen declarado`
              }
            />
            <ComputationRow term="Lectura de la ventaja" value={leadRatioReading(computation.lead_ratio)} />
          </dl>
        </section>
      ) : null}

      <details className="rounded-xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">
          ¿Cómo se ha evaluado esta ficha? (probabilidades de Clef y versiones)
        </summary>
        <div className="mt-3 flex flex-col gap-2 text-sm text-slate-700">
          <p>
            Lectura del texto: {pollTypeLabel(report.poll_type)}
            {pollProbs.length > 0 ? ". Probabilidades por opción:" : "."}
          </p>
          {pollProbs.length > 0 ? (
            <ul className="ml-4 list-disc">
              {pollProbs.map(([option, probability]) => (
                <li key={option}>
                  {pollTypeLabel(option)}: {formatPercent(probability)}
                </li>
              ))}
            </ul>
          ) : null}
          <p>
            Cuestionario v{report.questionnaire_version} · Lista de comprobación v
            {report.checklist_version}
          </p>
        </div>
      </details>

      <button
        type="button"
        onClick={onBack}
        className="self-start rounded-lg border border-slate-400 px-4 py-2 font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-slate-900"
      >
        Analizar otro texto
      </button>
    </main>
  );
}
