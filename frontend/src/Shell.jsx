import { useState } from "react";
import { useGlobalStore } from "./store";
import { fetchWithProject } from "./api";
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
      fetchWithProject(`/cached/cleaned/${encodeURIComponent(filename)}`).then(r => r.text()),
      fetchWithProject(`/cached/atoms/${encodeURIComponent(filename)}`).then(r => r.json()),
      fetchWithProject(`/cached/annotated/${encodeURIComponent(filename)}`).then(r => r.json()),
      fetchWithProject(`/cached/graph/${encodeURIComponent(filename)}`).then(r => r.json())
    ]);
    return { name: filename, cleaned, atoms, annotated, graph };
  }

  async function handleFiles(selectedFiles) {
    if (!selectedFiles.length) return;

    setStatusMessage("Uploading PDF(s)…");

    const form = new FormData();
    selectedFiles.forEach((f) => form.append("files", f));
    await fetchWithProject("/upload", {
      method: "POST",
      body: form,
    });

    const updated = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const filename = file.name;

      setStatusMessage(`Cleaning: ${filename} (${i+1}/${selectedFiles.length})`);
      const normRes = await fetchWithProject(`/normalize/${encodeURIComponent(filename)}`);
      const { content: cleaned } = await normRes.json();

      setStatusMessage(`Atomizing: ${filename} (${i+1}/${selectedFiles.length})`);
      const atomRes = await fetchWithProject(`/atomise/${encodeURIComponent(filename)}`);
      const { atoms } = await atomRes.json();

      setStatusMessage(`Annotating: ${filename} (${i+1}/${selectedFiles.length})`);
      const annotated = await (
        await fetchWithProject(`/annotate?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(atoms),
        })
      ).json();

      setStatusMessage(`Graphing: ${filename} (${i+1}/${selectedFiles.length})`);
      const graph = await (
        await fetchWithProject(`/graph?filename=${encodeURIComponent(filename)}`, {
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

  function handleFileSelect(index) {
    setActiveFileIndex(index);
    setSelectedFile(files[index]?.name || null);
    if (stage === -1) setStage(0); // If on upload stage, move to transcript
  }

  return (
    <div className="shell">
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