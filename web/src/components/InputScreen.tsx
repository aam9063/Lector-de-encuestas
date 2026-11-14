import { EXAMPLE_FULL, EXAMPLE_INCOMPLETE } from "../data/examples";

interface InputScreenProps {
  text: string;
  onTextChange: (value: string) => void;
  onSubmit: () => void;
  onLoadExample: (example: string) => void;
  loading: boolean;
  errorMessage: string | null;
}

export function InputScreen({
  text,
  onTextChange,
  onSubmit,
  onLoadExample,
  loading,
  errorMessage,
}: InputScreenProps) {
  const canSubmit = text.trim().length > 0 && !loading;

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-slate-900">Lector de fichas técnicas</h1>
        <p className="text-sm text-slate-600">
          Pega una noticia sobre una encuesta y mira qué información necesaria aparece y cuál
          falta, sin leer nada más.
        </p>
      </header>

      <div
        role="note"
        className="rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-800"
      >
        <strong>No es asesoramiento jurídico.</strong> La valoración jurídica corresponde a la
        Junta Electoral Central. Esta ficha describe la información que da la noticia, no la
        calidad de la encuesta.
      </div>

      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label htmlFor="news-text" className="font-semibold text-slate-900">
          Texto de la noticia
        </label>
        <textarea
          id="news-text"
          className="min-h-56 w-full rounded-lg border border-slate-300 p-3 text-sm focus-visible:outline-2 focus-visible:outline-slate-900"
          placeholder="Pega aquí el texto de la noticia..."
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
        />
        {errorMessage !== null ? (
          <p role="alert" className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900">
            {errorMessage}
          </p>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white hover:bg-slate-700 focus-visible:outline-2 focus-visible:outline-slate-900 disabled:opacity-40"
          >
            {loading ? "Analizando…" : "Analizar"}
          </button>
          {loading ? (
            <p role="status" className="text-sm text-slate-600">
              Analizando el texto: dura unos segundos.
            </p>
          ) : null}
        </div>
      </form>

      <section aria-label="Noticias de ejemplo" className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-sm font-bold text-slate-900">Noticias de ejemplo</h2>
        <p className="text-sm text-slate-600">
          Son simulaciones con entidades ficticias y datos inventados, marcadas desde el título
          como SIMULACIÓN. No son noticias reales.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onLoadExample(EXAMPLE_FULL)}
            disabled={loading}
            className="rounded-lg border border-slate-400 px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-slate-900 disabled:opacity-40"
          >
            Ejemplo completo (simulación)
          </button>
          <button
            type="button"
            onClick={() => onLoadExample(EXAMPLE_INCOMPLETE)}
            disabled={loading}
            className="rounded-lg border border-slate-400 px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-slate-900 disabled:opacity-40"
          >
            Ejemplo incompleto (simulación)
          </button>
        </div>
      </section>
    </main>
  );
}
