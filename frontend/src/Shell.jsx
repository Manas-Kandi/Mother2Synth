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
  const error = useGlobalStore((state) => state.error);
  const setError = useGlobalStore((state) => state.setError);

  async function loadCached(filename) {
    const [cleanedRes, atomsRes, annotatedRes, graphRes] = await Promise.all([
      fetch(`http://localhost:8000/cached/cleaned/${encodeURIComponent(filename)}`),
      fetch(`http://localhost:8000/cached/atoms/${encodeURIComponent(filename)}`),
      fetch(`http://localhost:8000/cached/annotated/${encodeURIComponent(filename)}`),
      fetch(`http://localhost:8000/cached/graph/${encodeURIComponent(filename)}`)
    ]);
    const cleaned = await cleanedRes.text();
    const atoms = await atomsRes.json();
    const annotated = await annotatedRes.json();
    const graph = await graphRes.json();
    return { name: filename, cleaned, atoms, annotated, graph };
  }

  async function handleFiles(selectedFiles) {
    if (!selectedFiles.length) return;

    setError(null);
    setStatusMessage("Uploading PDF(s)…");

    const form = new FormData();
    selectedFiles.forEach((f) => form.append("files", f));
    const upRes = await fetch("http://localhost:8000/upload", {
      method: "POST",
      body: form,
    });
    if (!upRes.ok) {
      const data = await upRes.json().catch(() => ({}));
      setError(data.detail || data.error || "Upload failed");
      return;
    }

    const updated = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const filename = file.name;

      setStatusMessage(`Cleaning: ${filename} (${i+1}/${selectedFiles.length})`);
      const normRes = await fetch(`http://localhost:8000/normalize/${encodeURIComponent(filename)}`);
      if (!normRes.ok) {
        const data = await normRes.json().catch(() => ({}));
        setError(data.detail || data.error || "Normalize failed");
        return;
      }
      const { content: cleaned } = await normRes.json();

      setStatusMessage(`Atomizing: ${filename} (${i+1}/${selectedFiles.length})`);
      const atomRes = await fetch(`http://localhost:8000/atomise/${encodeURIComponent(filename)}`);
      if (!atomRes.ok) {
        const data = await atomRes.json().catch(() => ({}));
        setError(data.detail || data.error || "Atomise failed");
        return;
      }
      const { atoms } = await atomRes.json();

      setStatusMessage(`Annotating: ${filename} (${i+1}/${selectedFiles.length})`);
      const annRes = await fetch(`http://localhost:8000/annotate?filename=${encodeURIComponent(filename)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(atoms),
      });
      if (!annRes.ok) {
        const data = await annRes.json().catch(() => ({}));
        setError(data.detail || data.error || "Annotate failed");
        return;
      }
      const annotated = await annRes.json();

      setStatusMessage(`Graphing: ${filename} (${i+1}/${selectedFiles.length})`);
      const graphRes = await fetch(`http://localhost:8000/graph?filename=${encodeURIComponent(filename)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(annotated),
      });
      if (!graphRes.ok) {
        const data = await graphRes.json().catch(() => ({}));
        setError(data.detail || data.error || "Graph failed");
        return;
      }
      const graph = await graphRes.json();

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

  function handleFileSelect(index) {
    setActiveFileIndex(index);
    setSelectedFile(files[index]?.name || null);
    if (stage === -1) setStage(0); // If on upload stage, move to transcript
  }

  return (
    <div className="shell">
      {error && <div className="error-banner">{error}</div>}
      <nav className="rail">
        <div className="rail-section">
          <h3 className="rail-title">Pipeline</h3>
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
        </div>

        {files.length > 0 && (
          <div className="rail-section">
            <h3 className="rail-title">Files</h3>
            {files.map((file, index) => (
              <button
                key={file.name}
                className={`file-item ${index === activeFileIndex ? "active" : ""}`}
                onClick={() => handleFileSelect(index)}
                title={file.name}
              >
                <span className="file-icon">📄</span>
                <span className="file-name">
                  {file.name.length > 18 ? `${file.name.substring(0, 18)}...` : file.name}
                </span>
              </button>
            ))}
          </div>
        )}
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