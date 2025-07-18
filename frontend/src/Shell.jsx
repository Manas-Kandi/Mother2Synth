import { useState } from "react";
import "./Shell.css";
import TranscriptStage from "./TranscriptStage";
import AtomsStage from "./AtomsStage";
import AnnotatedAtomsStage from "./AnnotatedAtomsStage";
import UploadStage from "./UploadStage";
import GraphStage from "./GraphStage";

export default function Shell() {
  const [active, setActive] = useState(-1); // -1: Upload, 0: Transcript, 1: Atoms, 2: Annotations, 3: Graph
  const [cleaned, setCleaned] = useState("");
  const [atoms, setAtoms] = useState([]);
  const [annotated, setAnnotated] = useState([]);
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [statusMessage, setStatusMessage] = useState("");

  const stages = [
    { id: -1, label: "Upload", state: "upload" },
    { id: 0, label: "Transcript", state: "done" },
    { id: 1, label: "Atoms",      state: "done" },
    { id: 2, label: "Annotations",   state: "pending" },
    { id: 3, label: "Graph",   state: "pending" },
  ];

  async function handleFiles(files) {
    if (!files.length) return;
    setStatusMessage("Uploading PDF…");
    const form = new FormData();
    files.forEach(f => form.append("files", f));
    await fetch("http://localhost:8000/upload", { method: "POST", body: form });
    setStatusMessage("Cleaning transcript…");
    const norm = await (await fetch("http://localhost:8000/normalize")).json();
    setCleaned(norm[files[0].name] || "");
    setStatusMessage("Atomizing…");
    const atomsRes = await (await fetch("http://localhost:8000/atomise")).json();
    setAtoms(atomsRes[files[0].name] || []);
    setStatusMessage("Annotating…");
    const annotatedRes = await (
      await fetch("http://localhost:8000/annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(atomsRes[files[0].name] || []),
      })
    ).json();
    setAnnotated(annotatedRes);
    setStatusMessage("Building graph…");
    const graphRes = await (
      await fetch("http://localhost:8000/graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(annotatedRes),
      })
    ).json();
    setGraph(graphRes);
    setStatusMessage("Done. Ready to view.");
    setActive(0);
  }

  return (
    <div className="shell">
      <nav className="rail">
        <button className={`step ${active === -1 ? "active" : ""}`} onClick={() => setActive(-1)}>
          <span className="dot done"></span>
          <span className="label">Upload</span>
        </button>
        <button className={`step ${active === 0 ? "active" : ""}`} onClick={() => setActive(0)}>
          <span className="dot done"></span>
          <span className="label">Transcript</span>
        </button>
        <button className={`step ${active === 1 ? "active" : ""}`} onClick={() => setActive(1)}>
          <span className="dot done"></span>
          <span className="label">Atoms</span>
        </button>
        <button className={`step ${active === 2 ? "active" : ""}`} onClick={() => setActive(2)}>
          <span className="dot pending"></span>
          <span className="label">Annotations</span>
        </button>
        <button className={`step ${active === 3 ? "active" : ""}`} onClick={() => setActive(3)}>
          <span className="dot pending">○</span>
          <span className="label">Graph</span>
        </button>
      </nav>
      <main className="stage">
        {active === -1 && <UploadStage onFiles={handleFiles} statusMessage={statusMessage} />}
        {active === 0 && <TranscriptStage transcript={cleaned} />}
        {active === 1 && <AtomsStage atoms={atoms} />}
        {active === 2 && <AnnotatedAtomsStage annotatedAtoms={annotated} />}
        {active === 3 && <GraphStage graph={graph} />}
      </main>
    </div>
  );
}
