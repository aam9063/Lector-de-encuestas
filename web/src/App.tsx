import { useCallback, useEffect, useState } from "react";
import { ApiError, analyzeText, analyzeUrl, getChecklist } from "./api/client";
import type { Checklist, Report } from "./api/types";
import { InputScreen, type InputMode } from "./components/InputScreen";
import { Sheet } from "./components/Sheet";
import { VedaNotice } from "./components/VedaNotice";

function App() {
  const [mode, setMode] = useState<InputMode>("text");
  const [pastedText, setPastedText] = useState("");
  const [url, setUrl] = useState("");
  const [fromUrl, setFromUrl] = useState(false);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<Checklist | null>(null);

  // The checklist is data from the API, never a copy inside this codebase.
  useEffect(() => {
    let cancelled = false;
    getChecklist()
      .then((fetched) => {
        if (!cancelled) setChecklist(fetched);
      })
      .catch(() => {
        // Without the checklist the sheet falls back to humanized item ids.
        if (!cancelled) setChecklist(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const analyze = useCallback(
    async (kind: InputMode, value: string) => {
      const trimmed = value.trim();
      if (trimmed.length === 0 || loading) return;
      setLoading(true);
      setErrorMessage(null);
      try {
        const nextReport = kind === "url" ? await analyzeUrl(trimmed) : await analyzeText(trimmed);
        setFromUrl(kind === "url");
        setReport(nextReport);
      } catch (error) {
        const message =
          error instanceof ApiError ? error.message : "Ha ocurrido un error inesperado.";
        setErrorMessage(message);
      } finally {
        setLoading(false);
      }
    },
    [loading],
  );

  const backToInput = useCallback(() => setReport(null), []);
  const loadExample = useCallback(
    (example: string) => {
      setPastedText(example);
    },
    [],
  );

  if (report === null) {
    return (
      <InputScreen
        mode={mode}
        onModeChange={setMode}
        text={pastedText}
        onTextChange={setPastedText}
        url={url}
        onUrlChange={setUrl}
        onSubmit={() => void analyze(mode, mode === "text" ? pastedText : url)}
        onLoadExample={loadExample}
        loading={loading}
        errorMessage={errorMessage}
      />
    );
  }

  if (report.status === "veda") {
    return <VedaNotice report={report} onBack={backToInput} />;
  }

  return (
    <Sheet
      report={report}
      pastedText={pastedText}
      fromUrl={fromUrl}
      checklist={checklist}
      onBack={backToInput}
    />
  );
}

export default App;
