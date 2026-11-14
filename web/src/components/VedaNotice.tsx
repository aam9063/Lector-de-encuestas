import type { Report } from "../api/types";

interface VedaNoticeProps {
  report: Report;
  onBack: () => void;
}

/**
 * Inside the blackout window there are no findings, only the notice: the backend
 * disclaimer carries the window dates and the reason, so the web shows it verbatim.
 */
export function VedaNotice({ report, onBack }: VedaNoticeProps) {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Lector de fichas técnicas</h1>
      </header>
      <section
        role="alert"
        aria-label="Aviso de veda electoral"
        className="rounded-2xl bg-slate-800 p-6 text-white"
      >
        <p className="flex items-center gap-3">
          <span aria-hidden="true" className="text-4xl font-bold">
            ⏸
          </span>
          <span className="text-3xl font-bold">Veda electoral</span>
        </p>
        <p className="mt-4 max-w-prose whitespace-pre-line text-sm leading-relaxed">
          {report.disclaimer}
        </p>
      </section>
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
