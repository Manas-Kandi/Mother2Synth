import { useState } from "react";
import { useGlobalStore } from "./store";
import "./Shell.css";
import UploadStage from "./UploadStage";
import TranscriptStage from "./TranscriptStage";
import AtomsStage from "./AtomsStage";
import AnnotatedAtomsStage from "./AnnotatedAtomsStage";
import GraphStage from "./GraphStage";

export default function Shell() {
  const [stage, setStage] = useState(-1); // -1: Upload, 0: Transcript, 1: Atoms, 2: Annotations, 3: Graph
  const [files, setFiles] = useState([]); // List of { name, cleaned, atoms, annotated, graph }
  const [activeFileIndex, setActiveFileIndex] = useState(null); // null until one is clicked
  const [statusMessage, setStatusMessage] = useState("");
  const setSelectedFile = useGlobalStore((state) => state.setSelectedFile);

  async function loadCached(filename) {
    const [cleaned, atoms, annotated, graph] = await Promise.all([
      fetch(`http://localhost:8000/cached/cleaned/${encodeURIComponent(filename)}`).then(r => r.text()),
      fetch(`http://localhost:8000/cached/atoms/${encodeURIComponent(filename)}`).then(r => r.json()),
      fetch(`http://localhost:8000/cached/annotated/${encodeURIComponent(filename)}`).then(r => r.json()),
      fetch(`http://localhost:8000/cached/graph/${encodeURIComponent(filename)}`).then(r => r.json())
    ]);
    return { name: filename, cleaned, atoms, annotated, graph };
  }

  async function handleFiles(selectedFiles) {
    if (!selectedFiles.length) return;

    setStatusMessage("Uploading PDF(s)…");

    const form = new FormData();
    selectedFiles.forEach((f) => form.append("files", f));
    await fetch("http://localhost:8000/upload", {
      method: "POST",
      body: form,
    });

    const updated = [];

    for (const file of selectedFiles) {
      const filename = file.name;

      setStatusMessage(`Cleaning: ${filename}`);
      const norm = await (await fetch("http://localhost:8000/normalize")).json();
      const cleaned = norm[filename] || "";

      setStatusMessage(`Atomizing: ${filename}`);
      const atomised = await (await fetch("http://localhost:8000/atomise")).json();
      const atoms = atomised[filename] || [];

      setStatusMessage(`Annotating: ${filename}`);
      const annotated = await (
        await fetch(`http://localhost:8000/annotate?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(atoms),
        })
      ).json();

      setStatusMessage(`Graphing: ${filename}`);
      const graph = await (
        await fetch(`http://localhost:8000/graph?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(annotated),
        })
      ).json();

      updated.push({ name: filename, cleaned, atoms, annotated, graph });
      console.log("✅ Adding file to state:", {
        name: filename,
        cleaned,
        atoms,
        annotated,
        graph
      });
    }

    const newFiles = [...files, ...updated];
    setFiles(newFiles);
    setActiveFileIndex(newFiles.length - updated.length); // select first of new batch
    setSelectedFile(newFiles[newFiles.length - updated.length]?.name || null); // set global selectedFile
    setStage(0);
    setStatusMessage("Done.");
  }

  function getActiveFile() {
    return activeFileIndex != null ? files[activeFileIndex] : null;
  }

  return (
    <div className="shell">
      <nav className="rail">
        <button className={`step ${stage === -1 ? "active" : ""}`} onClick={() => setStage(-1)}>
          <span className="dot"></span> <span className="label">Upload</span>
        </button>
        <button className={`step ${stage === 0 ? "active" : ""}`} onClick={() => setStage(0)}>
          <span className="dot"></span> <span className="label">Transcript</span>
        </button>
        <button className={`step ${stage === 1 ? "active" : ""}`} onClick={() => setStage(1)}>
          <span className="dot"></span> <span className="label">Atoms</span>
        </button>
        <button className={`step ${stage === 2 ? "active" : ""}`} onClick={() => setStage(2)}>
          <span className="dot"></span> <span className="label">Annotations</span>
        </button>
        <button className={`step ${stage === 3 ? "active" : ""}`} onClick={() => setStage(3)}>
          <span className="dot"></span> <span className="label">Graph</span>
        </button>
      </nav>

      <main className="stage">
        {stage === -1 && (
          <UploadStage
            onFiles={handleFiles}
            statusMessage={statusMessage}
            onJump={async (filename) => {
              const loaded = await loadCached(filename);
              setFiles([...files, loaded]);
              setActiveFileIndex(files.length);
              setSelectedFile(filename); // set global selectedFile on jump
              setStage(0);
            }}
          />
        )}

        {stage === 0 && <TranscriptStage file={getActiveFile()} />}
        {stage === 1 && <AtomsStage file={getActiveFile()} />}
        {stage === 2 && <AnnotatedAtomsStage file={getActiveFile()} />}
        {stage === 3 && <GraphStage file={getActiveFile()} />}
      </main>
    </div>
  );
}
