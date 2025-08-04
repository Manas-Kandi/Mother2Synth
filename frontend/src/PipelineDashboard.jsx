import { useState, useEffect } from "react";
import "./PipelineDashboard.css";
import { fetchWithProject } from "./api";
import SynthesisDoc from "./SynthesisDoc";

export default function PipelineDashboard({ files }) {
  const [status, setStatus] = useState({}); // { step, state, data }
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!files || !files.length) return;

    (async () => {
      // 1. Upload
      const form = new FormData();
      files.forEach(f => form.append("files", f));
      setStatus({ upload: { state: "running" }, step: "upload" });
      await fetchWithProject("/upload", { method: "POST", body: form });
      setStatus(s => ({ ...s, upload: { state: "done" }, step: "upload" }));

      // 2. Normalize
      setStatus(s => ({ ...s, normalize: { state: "running" }, step: "normalize" }));
      const normRes = await fetchWithProject("/normalize");
      const norm = await normRes.json();
      setStatus(s => ({ ...s, normalize: { state: "done", data: norm }, step: "normalize" }));

      // 3. Atomise
      setStatus(s => ({ ...s, atomise: { state: "running" }, step: "atomise" }));
      const atomRes = await fetchWithProject("/atomise");
      const atoms = await atomRes.json();
      setStatus(s => ({ ...s, atomise: { state: "done", data: atoms }, step: "atomise" }));

      // 4. Annotate
      setStatus(s => ({ ...s, annotate: { state: "running" }, step: "annotate" }));
      const annRes = await fetchWithProject("/annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.values(atoms).flat().flat())
      });
      const annotated = await annRes.json();
      setStatus(s => ({ ...s, annotate: { state: "done", data: annotated }, step: "annotate" }));
    })();
  }, [files]);

  // If all steps are done, show the SynthesisDoc view for the first file
  const fileKey = files[0]?.name;
  if (
    status.normalize?.data?.[fileKey] &&
    status.atomise?.data?.[fileKey] &&
    status.annotate?.data
  ) {
    return (
      <SynthesisDoc
        cleaned={status.normalize.data[fileKey] || ""}
        atoms={status.atomise.data[fileKey] || []}
        annotated={status.annotate.data || []}
      />
    );
  }

  // Otherwise, show the pipeline dashboard
  const steps = ["upload", "normalize", "atomise", "annotate"];
  const labels = {
    upload: "Upload PDFs",
    normalize: "Clean & label speakers",
    atomise: "Break into idea atoms",
    annotate: "Tag speech-act + sentiment"
  };

  return (
    <div className="dashboard">
      <h1>Pipeline</h1>
      {steps.map(step => (
        <section key={step} className="card">
          <header onClick={() => setExpanded(exp => (exp === step ? null : step))}>
            <StatusIcon state={status[step]?.state} />
            <span>{labels[step]}</span>
            <span className="chevron">{expanded === step ? "▲" : "▼"}</span>
          </header>

          {expanded === step && status[step]?.state === "done" && (
            <pre>
              {JSON.stringify(status[step].data, null, 2)}
            </pre>
          )}
        </section>
      ))}
    </div>
  );
}

function StatusIcon({ state }) {
  if (state === "done") return <span className="icon done">●</span>;
  if (state === "running") return <span className="icon running">◐</span>;
  if (state === "error") return <span className="icon error">●</span>;
  return <span className="icon idle">○</span>;
}
