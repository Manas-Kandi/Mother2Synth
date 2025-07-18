import { useState } from "react";
import "./Shell.css";
import TranscriptStage from "./TranscriptStage";
import AtomsStage from "./AtomsStage";
import AnnotatedAtomsStage from "./AnnotatedAtomsStage";

export default function Shell() {
  const [active, setActive] = useState(-1);
  const [cleaned, setCleaned] = useState("");
  const [atoms, setAtoms] = useState([]);
  const [annotated, setAnnotated] = useState([]);

  const stages = [
    { id: -1, label: "Upload", state: "upload" },
    { id: 0, label: "Transcript", state: "done" },
    { id: 1, label: "Atoms",      state: "done" },
    { id: 2, label: "Annotations",   state: "pending" },
  ];

  async function handleFiles(files) {
    if (!files.length) return;

    // 1. Upload
    const form = new FormData();
    files.forEach(f => form.append("files", f));
    await fetch("http://localhost:8000/upload", { method: "POST", body: form });

    // 2. Normalize
    const norm = await (await fetch("http://localhost:8000/normalize")).json();
    setCleaned(norm[files[0].name] || "");

    // 3. Atomise
    const atoms = await (await fetch("http://localhost:8000/atomise")).json();
    setAtoms(atoms[files[0].name] || []);

    // 4. Annotate
    const annotated = await (
      await fetch("http://localhost:8000/annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(atoms[files[0].name] || []),
      })
    ).json();
    setAnnotated(annotated);

    // 5. Auto-navigate to Transcript view
    setActive(0);
  }

  return (
    <div className="shell">
      <nav className="rail">
        {stages.map((s) => (
          <button
            key={s.id}
            className={`step ${active === s.id ? "active" : ""}`}
            onClick={() => setActive(s.id)}
          >
            <StateDot state={s.state} />
            <span className="label">{s.label}</span>
          </button>
        ))}
      </nav>

      <main className="stage">
        {active === -1 && <UploadStage onFiles={handleFiles} />}
        {active === 0 && <TranscriptStage transcript={cleaned} />}
        {active === 1 && <AtomsStage atoms={atoms} />}
        {active === 2 && <AnnotatedAtomsStage annotatedAtoms={annotated} />}
      </main>
    </div>
  );
}

function UploadStage({ onFiles }) {
  return (
    <section className="upload-stage">
      <label>
        <input
          type="file"
          accept="application/pdf"
          multiple
          onChange={(e) => onFiles(Array.from(e.target.files))}
        />
        <p>Drop PDFs here or click to select</p>
      </label>
    </section>
  );
}

function StateDot({ state }) {
  const cls = {
    done: "dot done",
    pending: "dot pending",
    active: "dot active",
    upload: "dot done"
  }[state];
  return <span className={cls} />;
}
