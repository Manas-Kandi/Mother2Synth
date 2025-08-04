import { useState, useEffect, useCallback } from "react";
import { useGlobalStore } from "./store";
import { fetchWithProject } from "./api";
import "./ComprehensiveShell.css";

// Import all stage components
import UploadStage from "./UploadStage";
import TranscriptStage from "./TranscriptStage";
import AtomsStage from "./AtomsStage";
import AnnotatedAtomsStage from "./AnnotatedAtomsStage";
import GraphStage from "./GraphStage";
import QualityGuardStage from "./QualityGuardStage";
import ChatAssistantStage from "./ChatAssistantStage";
import BoardStage from "./BoardStage";
import HumanCheckpointsStage from "./HumanCheckpointsStage";

// Navigation stages
const STAGES = {
  UPLOAD: -1,
  TRANSCRIPT: 0,
  ATOMS: 1,
  ANNOTATIONS: 2,
  GRAPH: 3,
  HUMAN_CHECKPOINTS: 4,
  BOARD: 5,
  QUALITY_GUARD: 6,
  CHAT_ASSISTANT: 7
};

export default function ComprehensiveShell() {
  const [stage, setStage] = useState(STAGES.UPLOAD);
  const [files, setFiles] = useState([]);
  const [activeFileIndex, setActiveFileIndex] = useState(null);
  const [statusMessage, setStatusMessage] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [currentContext, setCurrentContext] = useState({});
  
  const setSelectedFile = useGlobalStore((state) => state.setSelectedFile);

  // Context for chat assistant and quality guard
  const updateContext = useCallback(() => {
    const activeFile = activeFileIndex !== null ? files[activeFileIndex] : null;
    setCurrentContext({
      project: projectSlug,
      filename: activeFile?.name,
      stage: stage,
      themes: activeFile?.graph?.themes || [],
      atoms: activeFile?.atoms || [],
      insights: activeFile?.annotated?.insights || [],
      board: activeFile?.board || {}
    });
  }, [projectSlug, files, activeFileIndex, stage]);

  useEffect(() => {
    updateContext();
  }, [updateContext]);

  async function handleFiles(selectedFiles, slug) {
    if (!selectedFiles.length) return;

    if (!slug) {
      setStatusMessage("Project slug is required.");
      return;
    }

    try {
      const res = await fetchWithProject("/projects", {}, slug);
      const projects = await res.json();
      if (!projects[slug]) {
        setStatusMessage("Project slug not found.");
        return;
      }
    } catch (err) {
      console.error("Error validating slug", err);
      setStatusMessage("Error validating project slug.");
      return;
    }

    setProjectSlug(slug);
    setStatusMessage("Processing files...");

    const updated = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      try {
        const file = selectedFiles[i];
        const filename = file.name;

        // Step 1: Upload and normalize
        setStatusMessage(`Cleaning: ${filename} (${i+1}/${selectedFiles.length})`);
        const form = new FormData();
        form.append("files", file);
          const uploadRes = await fetchWithProject("/upload", {
            method: "POST",
            body: form,
          }, slug);
        if (!uploadRes.ok) {
          throw new Error(`Upload failed: ${uploadRes.statusText}`);
        }

        const normRes = await fetchWithProject(`/normalize/${encodeURIComponent(filename)}`, {}, slug);
        if (!normRes.ok) throw new Error(`Normalization failed: ${normRes.statusText}`);
        const { content: cleaned } = await normRes.json();

        // Step 2: Atomize
        setStatusMessage(`Atomizing: ${filename} (${i+1}/${selectedFiles.length})`);
        const atomRes = await fetchWithProject(`/atomise/${encodeURIComponent(filename)}`, {}, slug);
        if (!atomRes.ok) throw new Error(`Atomization failed: ${atomRes.statusText}`);
        const { atoms } = await atomRes.json();

        // Step 3: Annotate
        setStatusMessage(`Annotating: ${filename} (${i+1}/${selectedFiles.length})`);
        const annotateRes = await fetchWithProject(`/annotate?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(atoms),
        }, slug);
        if (!annotateRes.ok) throw new Error(`Annotation failed: ${annotateRes.statusText}`);
        const annotated = await annotateRes.json();

        // Step 4: Build graph
        setStatusMessage(`Building graph: ${filename} (${i+1}/${selectedFiles.length})`);
        const graphRes = await fetchWithProject(`/graph?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(annotated),
        }, slug);
        if (!graphRes.ok) throw new Error(`Graph build failed: ${graphRes.statusText}`);
        const graph = await graphRes.json();

        // Step 5: Create board
        setStatusMessage(`Creating board: ${filename} (${i+1}/${selectedFiles.length})`);
        const boardRes = await fetchWithProject("/board/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ atoms: annotated, themes: graph.themes, project_slug: slug, filename }),
        }, slug);
        if (!boardRes.ok) throw new Error(`Board creation failed: ${boardRes.statusText}`);
        const board = await boardRes.json();

        updated.push({
          name: filename,
          cleaned,
          atoms,
          annotated,
          graph,
          board,
          project_slug: slug,
          status: 'complete'
        });
      } catch (error) {
        console.error(`Error processing ${selectedFiles[i]?.name}:`, error);
        updated.push({
          name: selectedFiles[i]?.name || 'unknown',
          status: 'error',
          error: error.message
        });
      }

    }

    const newFiles = [...files, ...updated];
    setFiles(newFiles);
    setActiveFileIndex(newFiles.length - updated.length);
    setSelectedFile(newFiles[newFiles.length - updated.length]?.name || null);
    setStage(STAGES.TRANSCRIPT);
    setStatusMessage("Processing complete!");
    // Debug: log file structure after processing
    console.log("[DEBUG] Processed files:", newFiles);
  }

  function getActiveFile() {
    return activeFileIndex !== null ? files[activeFileIndex] : null;
  }

  function handleFileSelect(index) {
    setActiveFileIndex(index);
    setSelectedFile(files[index]?.name || null);
  }

  const getStageStatus = (stageKey) => {
    const activeFile = getActiveFile();
    if (!activeFile) return 'pending';

    switch (stageKey) {
      case STAGES.TRANSCRIPT:
        return activeFile.cleaned ? 'completed' : 'pending';
      case STAGES.ATOMS:
        return activeFile.atoms ? 'completed' : 'pending';
      case STAGES.ANNOTATIONS:
        return activeFile.annotated ? 'completed' : 'pending';
      case STAGES.GRAPH:
        return activeFile.graph ? 'completed' : 'pending';
      case STAGES.BOARD:
        return activeFile.board ? 'completed' : 'pending';
      default:
        return 'pending';
    }
  };

  const getStageIcon = (status) => {
    switch (status) {
      case 'completed': return '✅';
      case 'processing': return '⏳';
      case 'pending': return '⏸️';
      default: return '⏸️';
    }
  };

  return (
    <div className="comprehensive-shell">
      <nav className="comprehensive-rail">
        <div className="rail-section">
          <h3 className="rail-title">Research Pipeline</h3>
          
          {Object.entries({
            [STAGES.UPLOAD]: "Upload",
            [STAGES.TRANSCRIPT]: "Transcript",
            [STAGES.ATOMS]: "Atomize",
            [STAGES.ANNOTATIONS]: "Annotate",
            [STAGES.GRAPH]: "Analyze",
            [STAGES.HUMAN_CHECKPOINTS]: "Review",
            [STAGES.BOARD]: "Visualize",
            [STAGES.QUALITY_GUARD]: "Validate",
            [STAGES.CHAT_ASSISTANT]: "Assist"
          }).map(([key, label]) => {
            const stageKey = parseInt(key);
            const status = getStageStatus(stageKey);
            
            return (
              <button
                key={stageKey}
                className={`step ${stage === stageKey ? "active" : ""} ${status}`}
                onClick={() => setStage(stageKey)}
                disabled={status === 'pending' && stage !== stageKey}
              >
                <span className="step-icon">{getStageIcon(status)}</span>
                <span className="step-label">{label}</span>
                {status === 'processing' && <span className="step-spinner"></span>}
              </button>
            );
          })}
        </div>

        {files.length > 0 && (
          <div className="rail-section">
            <h3 className="rail-title">Research Files</h3>
            {files.map((file, index) => (
              <button
                key={file.name}
                className={`file-item ${index === activeFileIndex ? "active" : ""}`}
                onClick={() => handleFileSelect(index)}
                title={file.name}
              >
                <span className="file-icon">📄</span>
                <span className="file-name">
                  {file.name.length > 20 
                    ? `${file.name.substring(0, 20)}...` 
                    : file.name}
                </span>
                <div className="file-progress">
                  {[file.cleaned, file.atoms, file.annotated, file.graph, file.board]
                    .filter(Boolean).length}/5
                </div>
              </button>
            ))}
          </div>
        )}

        <div className="rail-section">
          <h3 className="rail-title">Project</h3>
          {projectSlug && (
            <div className="project-info">
              <span className="project-slug">{projectSlug}</span>
              <span className="file-count">{files.length} files</span>
            </div>
          )}
        </div>
      </nav>

      <main className="stage-content">
        {stage === STAGES.UPLOAD && (
          <UploadStage
            onFiles={handleFiles}
            statusMessage={statusMessage}
            projectSlug={projectSlug}
            setProjectSlug={setProjectSlug}
          />
        )}

        {stage === STAGES.TRANSCRIPT && (
          <TranscriptStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.ATOMS && (
          <AtomsStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.ANNOTATIONS && (
          <AnnotatedAtomsStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.GRAPH && (
          <GraphStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.HUMAN_CHECKPOINTS && (
          <HumanCheckpointsStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.BOARD && (
          <BoardStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.QUALITY_GUARD && (
          <QualityGuardStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}

        {stage === STAGES.CHAT_ASSISTANT && (
          <ChatAssistantStage 
            file={getActiveFile()} 
            context={currentContext}
          />
        )}
      </main>

      {/* Global status bar */}
      <div className="status-bar">
        <div className="status-left">
          {statusMessage && <span className="status-message">{statusMessage}</span>}
        </div>
        <div className="status-right">
          {getActiveFile() && (
            <span className="file-info">
              {getActiveFile().name} - Stage {stage + 1}/8
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
