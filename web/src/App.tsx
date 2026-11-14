import { useCallback, useEffect, useState } from "react";
import { ApiError, analyzeText, getChecklist } from "./api/client";
import type { Checklist, Report } from "./api/types";
import { InputScreen } from "./components/InputScreen";
import { Sheet } from "./components/Sheet";
import { VedaNotice } from "./components/VedaNotice";

function App() {
  const [pastedText, setPastedText] = useState("");
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
    async (value: string) => {
      const trimmed = value.trim();
      if (trimmed.length === 0 || loading) return;
      setLoading(true);
      setErrorMessage(null);
      try {
        const nextReport = await analyzeText(trimmed);
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
        text={pastedText}
        onTextChange={setPastedText}
        onSubmit={() => void analyze(pastedText)}
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
    <Sheet report={report} pastedText={pastedText} checklist={checklist} onBack={backToInput} />
  );
}

export default App;
