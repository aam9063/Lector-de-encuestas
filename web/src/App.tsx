import { useState } from "react";

function App() {
  const [text, setText] = useState("");

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-8">
      <header>
        <h1 className="text-2xl font-bold">Ficha Técnica</h1>
        <p className="text-sm text-gray-600">
          Pega una noticia sobre una encuesta y mira qué información necesaria aparece y
          cuál falta. No es asesoramiento jurídico: la valoración corresponde a la JEC.
        </p>
      </header>
      <textarea
        className="min-h-48 w-full rounded-lg border border-gray-300 p-3 text-sm"
        placeholder="Pega aquí el texto de la noticia..."
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      <button
        type="button"
        disabled
        title="Available once ENC-14 lands"
        className="rounded-lg bg-gray-800 px-4 py-2 font-semibold text-white disabled:opacity-40"
      >
        Analizar
      </button>
    </main>
  );
}

export default App;
