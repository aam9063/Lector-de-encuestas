import type { Finding } from "../api/types";
import { HighlightedText } from "./HighlightedText";
import { formatPercent, sourceLabel, STATUS_STYLES } from "../lib/labels";

interface FindingRowProps {
  finding: Finding;
  name: string;
  /** The user's own pasted text, needed to render the evidence highlights. */
  text: string;
  expanded: boolean;
  onToggle: (itemId: string) => void;
}

export function FindingRow({ finding, name, text, expanded, onToggle }: FindingRowProps) {
  const style = STATUS_STYLES[finding.status];
  const panelId = `finding-panel-${finding.item_id}`;
  const buttonId = `finding-button-${finding.item_id}`;

  return (
    <li className="rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        id={buttonId}
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={() => onToggle(finding.item_id)}
        className="flex w-full items-center gap-3 px-3 py-3 text-left hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-slate-900"
      >
        <span
          aria-hidden="true"
          className={`inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-bold ${style.badgeClass}`}
        >
          {style.icon}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-slate-900">{name}</span>
          <span className="block truncate text-sm text-slate-600">{finding.message}</span>
        </span>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${style.badgeClass}`}
        >
          <span aria-hidden="true">{style.icon}</span>
          {style.label}
        </span>
      </button>
      {expanded ? (
        <div id={panelId} role="region" aria-labelledby={buttonId} className="border-t border-slate-200 p-3">
          {finding.status === "review" ? (
            <p className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
              No estamos seguros con este punto: mira la frase resaltada en tu texto y revísalo a
              mano.
            </p>
          ) : null}
          <p className="mb-2 text-sm text-slate-600">
            Evaluado por {sourceLabel(finding.source)}.
            <span className="block sm:inline">
              {finding.probability === null
                ? " Clef no ha dado ninguna probabilidad para este punto."
                : ` Probabilidad de Clef: ${formatPercent(finding.probability)}.`}
            </span>
          </p>
          <HighlightedText text={text} spans={finding.evidence} />
        </div>
      ) : null}
    </li>
  );
}
