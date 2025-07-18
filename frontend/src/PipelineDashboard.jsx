import { useState, useEffect } from "react";

export default function PipelineDashboard({ files }) {
  const [status, setStatus] = useState({}); // { step: "idle|running|done|error", data: … }

  useEffect(() => {
    if (!files || !files.length) return;

    (async () => {
      // 1. Upload
      const form = new FormData();
      files.forEach(f => form.append("files", f));
      setStatus({ upload: { state: "running" }, step: "upload" });
      await fetch("http://localhost:8000/upload", { method: "POST", body: form });
      setStatus(s => ({ ...s, upload: { state: "done" }, step: "upload" }));

      // 2. Normalize
      setStatus(s => ({ ...s, normalize: { state: "running" }, step: "normalize" }));
      const normRes = await fetch("http://localhost:8000/normalize");
      const norm = await normRes.json();
      setStatus(s => ({ ...s, normalize: { state: "done", data: norm }, step: "normalize" }));

      // 3. Atomise
      setStatus(s => ({ ...s, atomise: { state: "running" }, step: "atomise" }));
      const atomRes = await fetch("http://localhost:8000/atomise");
      const atoms = await atomRes.json();
      setStatus(s => ({ ...s, atomise: { state: "done", data: atoms }, step: "atomise" }));

      // 4. Annotate
      setStatus(s => ({ ...s, annotate: { state: "running" }, step: "annotate" }));
      const annRes = await fetch("http://localhost:8000/annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.values(atoms).flat().flat())
      });
      const annotated = await annRes.json();
      setStatus(s => ({ ...s, annotate: { state: "done", data: annotated }, step: "annotate" }));
    })();
  }, [files]);

  const steps = ["upload", "normalize", "atomise", "annotate"];
  const labels = {
    upload: "Upload PDFs",
    normalize: "Clean & label speakers",
    atomise: "Break into idea atoms",
    annotate: "Tag speech-act + sentiment"
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h2>Pipeline Progress</h2>
      {steps.map(step => (
        <details key={step} open={status.step === step}>
          <summary>
            <StatusBadge state={status[step]?.state} /> {labels[step]}
          </summary>
          {status[step]?.state === "done" && (
            <pre style={{ fontSize: 12, maxHeight: 200, overflow: "auto" }}>
              {JSON.stringify(status[step].data, null, 2)}
            </pre>
          )}
        </details>
      ))}
    </div>
  );
}

function StatusBadge({ state }) {
  if (state === "done") return <span style={{ color: "lime" }}>✅</span>;
  if (state === "running") return <span style={{ color: "orange" }}>⏳</span>;
  if (state === "error") return <span style={{ color: "red" }}>❌</span>;
  return <span style={{ color: "#666" }}>⏸️</span>;
}
