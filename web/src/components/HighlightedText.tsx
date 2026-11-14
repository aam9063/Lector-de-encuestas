import type { Span } from "../api/types";

interface Segment {
  text: string;
  highlight: boolean;
  key: string;
}

/**
 * Splits the user's own text into plain and highlighted segments. Highlighting uses
 * text.slice(start, end) over the original text only: React escapes everything, no
 * dangerouslySetInnerHTML anywhere.
 */
function segment(text: string, spans: Span[]): Segment[] {
  const ordered = [...spans].sort((a, b) => a.start - b.start);
  const segments: Segment[] = [];
  let cursor = 0;
  for (const [index, span] of ordered.entries()) {
    const start = Math.max(cursor, Math.min(span.start, text.length));
    const end = Math.max(start, Math.min(span.end, text.length));
    if (end <= start) continue;
    if (start > cursor) {
      segments.push({ text: text.slice(cursor, start), highlight: false, key: `p${index}` });
    }
    segments.push({ text: text.slice(start, end), highlight: true, key: `h${index}` });
    cursor = end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), highlight: false, key: "tail" });
  }
  return segments;
}

interface HighlightedTextProps {
  text: string;
  spans: Span[];
  /** Height limit so a long story does not push the sheet off screen. */
  scrollable?: boolean;
}

export function HighlightedText({ text, spans, scrollable = true }: HighlightedTextProps) {
  const segments = segment(text, spans);
  return (
    <div
      className={`whitespace-pre-wrap rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm leading-relaxed text-slate-800 ${
        scrollable ? "max-h-80 overflow-y-auto" : ""
      }`}
    >
      {segments.map((segment) =>
        segment.highlight ? (
          <mark key={segment.key} className="rounded-sm bg-yellow-300 px-0.5 text-slate-900">
            {segment.text}
          </mark>
        ) : (
          <span key={segment.key}>{segment.text}</span>
        ),
      )}
      {segments.every((segment) => !segment.highlight) ? (
        <p className="mt-2 text-xs text-slate-600">
          No hay frases candidatas que resaltar para este punto.
        </p>
      ) : null}
    </div>
  );
}
