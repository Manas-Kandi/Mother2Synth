import { useState, useEffect, useCallback, useMemo } from "react";
import { useGlobalStore } from "./store";
import { fetchWithProject } from "./api";
import "./ComprehensiveShell.css";

import UploadStage from "./UploadStage";
import TranscriptStage from "./TranscriptStage";
import AtomsStage from "./AtomsStage";
import AnnotatedAtomsStage from "./AnnotatedAtomsStage";
import GraphStage from "./GraphStage";
import QualityGuardStage from "./QualityGuardStage";
import ChatAssistantStage from "./ChatAssistantStage";
import BoardStage from "./BoardStage";
import HumanCheckpointsStage from "./HumanCheckpointsStage";

const STAGES = {
  UPLOAD: -1,
  TRANSCRIPT: 0,
  ATOMS: 1,
  ANNOTATIONS: 2,
  GRAPH: 3,
  HUMAN_CHECKPOINTS: 4,
  BOARD: 5,
  QUALITY_GUARD: 6,
  CHAT_ASSISTANT: 7,
};

const STAGE_DETAILS = [
  { key: STAGES.UPLOAD, label: "Upload", description: "Add transcripts and project files" },
  { key: STAGES.TRANSCRIPT, label: "Transcript", description: "Review the cleaned transcript" },
  { key: STAGES.ATOMS, label: "Atoms", description: "Inspect extracted atomic insights" },
  { key: STAGES.ANNOTATIONS, label: "Annotations", description: "Enrich atoms with metadata" },
  { key: STAGES.GRAPH, label: "Graph", description: "Explore generated themes and links" },
  { key: STAGES.HUMAN_CHECKPOINTS, label: "Checkpoints", description: "Address human QA prompts" },
  { key: STAGES.BOARD, label: "Board", description: "Review the collaborative research board" },
  { key: STAGES.QUALITY_GUARD, label: "Quality", description: "Validate research quality" },
  { key: STAGES.CHAT_ASSISTANT, label: "Assistant", description: "Ask questions about the project" },
];

const STATUS_LABELS = {
  completed: "Done",
  active: "In progress",
  pending: "Pending",
};

export default function ComprehensiveShell() {
  const [stage, setStage] = useState(STAGES.UPLOAD);
  const [files, setFiles] = useState([]);
  const [activeFileIndex, setActiveFileIndex] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [currentContext, setCurrentContext] = useState({});

  const { projectSlug, setProjectSlug, setSelectedFile } = useGlobalStore((state) => state);

  const activeFile = activeFileIndex !== null ? files[activeFileIndex] : null;

  const updateContext = useCallback(() => {
    const file = activeFile;
    setCurrentContext({
      project: projectSlug,
      filename: file?.name,
      stage,
      themes: file?.graph?.themes || [],
      atoms: file?.atoms || [],
      insights: file?.annotated?.insights || [],
      quality: file?.quality || [],
      board: file?.board,
      file,
    });
  }, [activeFile, projectSlug, stage]);

  useEffect(() => {
    updateContext();
  }, [updateContext]);

  const handleFiles = async (selectedFiles, slug) => {
    if (!selectedFiles || !selectedFiles.length) {
      setStatusMessage("No files selected.");
      return;
    }

    if (!slug) {
      setStatusMessage("Project slug is required.");
      return;
    }

    setProjectSlug(slug);
    setStatusMessage(`Preparing to process ${selectedFiles.length} file(s)...`);

    try {
      const res = await fetchWithProject("/projects", {}, slug);
      if (res.ok) {
        const projects = await res.json();
        if (!projects[slug]) {
          setStatusMessage(`Creating new project '${slug}'...`);
        }
      }
    } catch (err) {
      console.warn("Project validation warning:", err);
    }

    const processedFiles = [];
    let encounteredError = false;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const filename = file.name;

      try {
        setStatusMessage(`Uploading ${filename} (${i + 1}/${selectedFiles.length})`);
        const form = new FormData();
        form.append("files", file);

        const uploadRes = await fetchWithProject(
          "/upload",
          {
            method: "POST",
            body: form,
          },
          slug
        );

        if (!uploadRes.ok) {
          throw new Error(`Upload failed: ${uploadRes.status}`);
        }

        await uploadRes.json();

        setStatusMessage(`Normalizing ${filename}`);
        const normalizeRes = await fetchWithProject(
          `/normalize?filename=${encodeURIComponent(filename)}`,
          { method: "POST" },
          slug
        );

        if (!normalizeRes.ok) {
          throw new Error(`Normalization failed: ${normalizeRes.status}`);
        }

        const normData = await normalizeRes.json();
        const cleaned = normData.content;

        setStatusMessage(`Atomizing ${filename}`);
        const atomiseRes = await fetchWithProject(
          `/atomise?filename=${encodeURIComponent(filename)}`,
          { method: "POST" },
          slug
        );

        if (!atomiseRes.ok) {
          throw new Error(`Atomization failed: ${atomiseRes.status}`);
        }

        const { atoms } = await atomiseRes.json();

        setStatusMessage(`Annotating ${filename}`);
        const annotateRes = await fetchWithProject(
          `/annotate?filename=${encodeURIComponent(filename)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(atoms),
          },
          slug
        );

        if (!annotateRes.ok) {
          throw new Error(`Annotation failed: ${annotateRes.status}`);
        }

        const annotated = await annotateRes.json();

        setStatusMessage(`Building graph for ${filename}`);
        const graphRes = await fetchWithProject(
          `/graph?filename=${encodeURIComponent(filename)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(annotated),
          },
          slug
        );

        if (!graphRes.ok) {
          throw new Error(`Graph build failed: ${graphRes.status}`);
        }

        const graph = await graphRes.json();

        setStatusMessage(`Generating themes for ${filename}`);
        const themesRes = await fetchWithProject(
          `/themes/initial?filename=${encodeURIComponent(filename)}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(annotated),
          },
          slug
        );

        if (!themesRes.ok) {
          throw new Error(`Initial themes fetch failed: ${themesRes.status}`);
        }

        const initialThemes = await themesRes.json();
        graph.themes = [...(graph.themes || []), ...initialThemes];

        setStatusMessage(`Creating board for ${filename}`);
        const boardRes = await fetchWithProject(
          "/board/create",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              atoms: annotated,
              themes: graph.themes,
              project_slug: slug,
              filename,
            }),
          },
          slug
        );

        if (!boardRes.ok) {
          throw new Error(`Board creation failed: ${boardRes.status}`);
        }

        const boardResponse = await boardRes.json();
        const board = { ...boardResponse.board, board_url: boardResponse.board_url };

        processedFiles.push({
          id: `${filename}-${new Date().toISOString()}`,
          name: filename,
          cleaned,
          atoms,
          annotated,
          graph,
          board,
          project_slug: slug,
          status: "complete",
          processedAt: new Date().toISOString(),
        });
      } catch (error) {
        console.error(`Error processing ${filename}:`, error);
        encounteredError = true;
        setStatusMessage(`Error processing ${filename}: ${error.message}`);
        processedFiles.push({
          id: `${filename}-${new Date().toISOString()}`,
          name: filename,
          status: "error",
          error: error.message,
        });
      }
    }

    const newFiles = [...files, ...processedFiles];
    setFiles(newFiles);

    if (!encounteredError && newFiles.length > 0) {
      const firstNewFileIndex = newFiles.length - processedFiles.length;
      setActiveFileIndex(firstNewFileIndex);
      setSelectedFile(newFiles[firstNewFileIndex]?.name || null);
      setStage(STAGES.TRANSCRIPT);
      setStatusMessage("Processing complete!");
    }
  };

  const handleFileSelect = (index) => {
    setActiveFileIndex(index);
    setSelectedFile(files[index]?.name || null);
  };

  const stageCompletion = useMemo(() => ({
    [STAGES.UPLOAD]: files.length > 0,
    [STAGES.TRANSCRIPT]: Boolean(activeFile?.cleaned),
    [STAGES.ATOMS]: Boolean(activeFile?.atoms && activeFile.atoms.length),
    [STAGES.ANNOTATIONS]: Boolean(activeFile?.annotated),
    [STAGES.GRAPH]: Boolean(activeFile?.graph),
    [STAGES.HUMAN_CHECKPOINTS]: Boolean(activeFile),
    [STAGES.BOARD]: Boolean(activeFile?.board),
    [STAGES.QUALITY_GUARD]: Boolean(activeFile?.quality),
    [STAGES.CHAT_ASSISTANT]: Boolean(activeFile),
  }), [files.length, activeFile]);

  const getStageStatus = useCallback((stageKey) => {
    if (stage === stageKey) return "active";
    if (stageCompletion[stageKey]) return "completed";
    return "pending";
  }, [stage, stageCompletion]);

  const canNavigateToStage = useCallback((stageKey) => {
    if (stageKey === STAGES.UPLOAD) return true;
    return Boolean(activeFile);
  }, [activeFile]);

  const stageTimeline = useMemo(
    () => STAGE_DETAILS.map((detail) => {
      const status = getStageStatus(detail.key);
      const disabled = !canNavigateToStage(detail.key) && stage !== detail.key;
      return {
        ...detail,
        status,
        disabled,
        isActive: stage === detail.key,
      };
    }),
    [getStageStatus, stage, canNavigateToStage]
  );

  const stageLabel = useMemo(
    () => STAGE_DETAILS.find((detail) => detail.key === stage)?.label || "Workspace",
    [stage]
  );

  return (
    <div className="comprehensive-shell">
      <aside className="shell-sidebar">
        <div className="sidebar-scroll">
          <div className="sidebar-header">
            <h2 className="sidebar-title">Mother2 Synth</h2>
            <span className="sidebar-subtitle">Project pipeline</span>
          </div>

          <section className="sidebar-section">
            <div className="section-label">Project</div>
            <input
              type="text"
              className="project-input"
              placeholder="Enter a project slug"
              value={projectSlug || ""}
              onChange={(e) => setProjectSlug(e.target.value)}
            />
            <p className="section-help">
              Choose a short identifier to group uploads and analysis outputs.
            </p>
          </section>

          <section className="sidebar-section">
            <div className="section-heading">
              <span className="section-label">Files</span>
              <span className="section-count">{files.length}</span>
            </div>
            <div className="file-list">
              {files.length === 0 ? (
                <div className="empty-block">No files processed yet.</div>
              ) : (
                files.map((file, index) => {
                  const isActive = index === activeFileIndex;
                  const hasError = file.status === "error";
                  return (
                    <button
                      key={file.id || file.name || index}
                      type="button"
                      className={`file-card ${isActive ? "active" : ""} ${hasError ? "error" : ""}`}
                      onClick={() => handleFileSelect(index)}
                    >
                      <div className="file-card-top">
                        <span className="file-name" title={file.name}>{file.name}</span>
                        <span className={`file-status ${file.status || "complete"}`}>
                          {file.status === "error" ? "Error" : "Ready"}
                        </span>
                      </div>
                      <div className="file-meta">
                        <span>{file.processedAt ? new Date(file.processedAt).toLocaleString() : "Pending"}</span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section className="sidebar-section">
            <div className="section-heading">
              <span className="section-label">Pipeline</span>
            </div>
            <div className="pipeline-list">
              {stageTimeline.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  className={`pipeline-step ${item.status} ${item.isActive ? "active" : ""}`}
                  onClick={() => !item.disabled && setStage(item.key)}
                  disabled={item.disabled}
                >
                  <span className="step-marker" aria-hidden="true"></span>
                  <div className="step-text">
                    <span className="step-title">{item.label}</span>
                    <span className="step-description">{item.description}</span>
                  </div>
                  <span className={`step-status ${item.status}`}>{STATUS_LABELS[item.status]}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      </aside>

      <div className="shell-main">
        <header className="shell-header">
          <div className="header-titles">
            <h1 className="header-title">{stageLabel}</h1>
            <div className="header-meta">
              <span>{projectSlug || "No project selected"}</span>
              {activeFile && <span>• {activeFile.name}</span>}
            </div>
          </div>
          {statusMessage && (
            <div className="header-status">
              <span className="status-pill" title={statusMessage}>{statusMessage}</span>
            </div>
          )}
        </header>

        <main className="shell-content">
          <div className="stage-surface">
            {stage === STAGES.UPLOAD && (
              <UploadStage
                onFiles={handleFiles}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.TRANSCRIPT && (
              <TranscriptStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.ATOMS && (
              <AtomsStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.ANNOTATIONS && (
              <AnnotatedAtomsStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.GRAPH && (
              <GraphStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.HUMAN_CHECKPOINTS && (
              <HumanCheckpointsStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.BOARD && (
              <BoardStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.QUALITY_GUARD && (
              <QualityGuardStage
                file={activeFile}
                onStatusChange={setStatusMessage}
              />
            )}
            {stage === STAGES.CHAT_ASSISTANT && (
              <ChatAssistantStage
                file={activeFile}
                context={currentContext}
                onStatusChange={setStatusMessage}
              />
            )}
          </div>
        </main>

        <footer className="shell-footer">
          <div className="footer-left">
            <span className="footer-dot" aria-hidden="true"></span>
            <span>{statusMessage || "Standing by for your next action"}</span>
          </div>
          <div className="footer-right">
            <span>{files.length} file{files.length === 1 ? "" : "s"}</span>
            <span>Stage: {stageLabel}</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
