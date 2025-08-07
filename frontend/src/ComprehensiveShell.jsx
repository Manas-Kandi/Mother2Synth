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
  const [currentContext, setCurrentContext] = useState({});
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activityBarVisible, setActivityBarVisible] = useState(true);
  
  const { projectSlug, setProjectSlug, setSelectedFile } = useGlobalStore((state) => state);

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
      quality: activeFile?.quality || [],
      board: activeFile?.board,
      file: activeFile
    });
  }, [files, activeFileIndex, stage, projectSlug]);

  useEffect(() => {
    updateContext();
  }, [updateContext]);

  const handleFiles = async (selectedFiles, slug) => {
    if (!selectedFiles || !selectedFiles.length) {
      console.error('No files selected');
      setStatusMessage("No files selected.");
      return;
    }

    if (!slug) {
      console.error('No project slug provided');
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
          console.log(`Project '${slug}' not found, will attempt to create during upload`);
          setStatusMessage(`Creating new project '${slug}'...`);
        }
      }
    } catch (err) {
      console.warn("Project validation warning:", err);
    }

    const updatedFiles = [];
    let encounteredError = false;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const filename = file.name;

      try {
        console.log(`Processing file ${i + 1}/${selectedFiles.length}: ${filename}`);

        // Step 1: Upload file
        setStatusMessage(`Uploading: ${filename} (${i + 1}/${selectedFiles.length})`);
        const form = new FormData();
        form.append("files", file);

        const uploadRes = await fetchWithProject("/upload", {
          method: "POST",
          body: form,
        }, slug);

        if (!uploadRes.ok) {
          throw new Error(`Upload failed: ${uploadRes.status}`);
        }

        await uploadRes.json();

        // Step 2: Normalize
        setStatusMessage(`Normalizing: ${filename} (${i + 1}/${selectedFiles.length})`);
        const normalizeRes = await fetchWithProject(`/normalize?filename=${encodeURIComponent(filename)}`, {
          method: "POST"
        }, slug);

        if (!normalizeRes.ok) {
          throw new Error(`Normalization failed: ${normalizeRes.status}`);
        }

        const normData = await normalizeRes.json();
        const cleaned = normData.content;

        // Step 3: Atomize
        setStatusMessage(`Processing: ${filename} (${i + 1}/${selectedFiles.length})`);
        const atomiseRes = await fetchWithProject(`/atomise?filename=${encodeURIComponent(filename)}`, {
          method: "POST"
        }, slug);

        if (!atomiseRes.ok) {
          throw new Error(`Atomization failed: ${atomiseRes.status}`);
        }

        const { atoms } = await atomiseRes.json();

        // Step 4: Annotate
        setStatusMessage(`Analyzing: ${filename} (${i + 1}/${selectedFiles.length})`);
        const annotateRes = await fetchWithProject(`/annotate?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(atoms),
        }, slug);

        if (!annotateRes.ok) {
          throw new Error(`Annotation failed: ${annotateRes.status}`);
        }

        const annotated = await annotateRes.json();

        // Step 5: Build graph
        setStatusMessage(`Building insights: ${filename} (${i + 1}/${selectedFiles.length})`);
        const graphRes = await fetchWithProject(`/graph?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(annotated),
        }, slug);

        if (!graphRes.ok) {
          throw new Error(`Graph build failed: ${graphRes.status}`);
        }

        const graph = await graphRes.json();

        // Step 6: Generate initial themes
        setStatusMessage(`Generating themes: ${filename} (${i + 1}/${selectedFiles.length})`);
        const themesRes = await fetchWithProject(`/themes/initial?filename=${encodeURIComponent(filename)}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(annotated),
        }, slug);

        if (!themesRes.ok) {
          throw new Error(`Initial themes fetch failed: ${themesRes.status}`);
        }

        const initialThemes = await themesRes.json();
        graph.themes = [...(graph.themes || []), ...initialThemes];

        // Step 7: Create board
        setStatusMessage(`Finalizing: ${filename} (${i + 1}/${selectedFiles.length})`);
        const boardRes = await fetchWithProject("/board/create", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            atoms: annotated,
            themes: graph.themes,
            project_slug: slug,
            filename
          }),
        }, slug);

        if (!boardRes.ok) {
          throw new Error(`Board creation failed: ${boardRes.status}`);
        }

        const boardResponse = await boardRes.json();
        const board = { ...boardResponse.board, board_url: boardResponse.board_url };

        const fileData = {
          id: `${filename}-${new Date().toISOString()}`,
          name: filename,
          cleaned,
          atoms,
          annotated,
          graph,
          board,
          project_slug: slug,
          status: 'complete',
          processedAt: new Date().toISOString()
        };

        updatedFiles.push(fileData);
      } catch (error) {
        console.error(`Error processing ${filename}:`, error);
        encounteredError = true;
        setStatusMessage(`Error processing ${filename}: ${error.message}`);
        updatedFiles.push({
          id: `${filename}-${new Date().toISOString()}`,
          name: filename,
          status: 'error',
          error: error.message
        });
      }
    }

    const newFiles = [...files, ...updatedFiles];
    setFiles(newFiles);
    if (!encounteredError && newFiles.length > 0) {
      const firstNewFileIndex = newFiles.length - updatedFiles.length;
      setActiveFileIndex(firstNewFileIndex);
      setSelectedFile(newFiles[firstNewFileIndex]?.name || null);
      setStage(STAGES.TRANSCRIPT);
      setStatusMessage("Processing complete!");
    }
  };

  const getStageStatus = (stageKey) => {
    const activeFile = activeFileIndex !== null ? files[activeFileIndex] : null;
    if (!activeFile) return 'pending';

    const stageMap = {
      [STAGES.UPLOAD]: 'complete',
      [STAGES.TRANSCRIPT]: activeFile.cleaned ? 'complete' : 'pending',
      [STAGES.ATOMS]: activeFile.atoms ? 'complete' : 'pending',
      [STAGES.ANNOTATIONS]: activeFile.annotated ? 'complete' : 'pending',
      [STAGES.GRAPH]: activeFile.graph ? 'complete' : 'pending',
      [STAGES.BOARD]: activeFile.board ? 'complete' : 'pending',
      [STAGES.QUALITY]: 'pending',
      [STAGES.CHAT]: 'pending',
    };

    return stageMap[stageKey] || 'pending';
  };

  const getStageIcon = (status) => {
    switch (status) {
      case 'complete':
        return '✓';
      case 'pending':
        return '○';
      case 'active':
        return '●';
      default:
        return '○';
    }
  };

  function getActiveFile() {
    return activeFileIndex !== null ? files[activeFileIndex] : null;
  }

  function handleFileSelect(index) {
    setActiveFileIndex(index);
    setSelectedFile(files[index]?.name || null);

  return board;
}
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

// Main component is already defined at the top of the file
// This file contains the ComprehensiveShell component and its helper functions
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65A.588.588 0 0 0 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.26 1.17-.59 1.69-.98l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66z" fill="currentColor"/>
          </svg>
        </div>
        <div className="activity-item" title="Chat Assistant">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" fill="currentColor"/>
          </svg>
        </div>
      </div>
    </div>

    {/* Sidebar */}
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <h2>Explorer</h2>
          <span className="project-badge">{projectSlug || 'No Project'}</span>
        </div>
      </div>

      {/* Project Section */}
      <div className="sidebar-section">
        <div className="section-header">
          <h3>Project</h3>
          <button className="section-action" title="New Project">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" fill="currentColor"/>
            </svg>
          </button>
        </div>
        <div className="project-input">
          <input
            type="text"
            placeholder="Project name..."
            value={projectSlug}
            onChange={(e) => setProjectSlug(e.target.value)}
            className="project-input-field"
          />
        </div>
      </div>

      {/* Files Section */}
      <div className="sidebar-section">
        <div className="section-header">
          <h3>Files</h3>
          <button className="section-action" title="Upload Files">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z" fill="currentColor"/>
            </svg>
          </button>
        </div>
        <div className="file-tree">
          {files.map((file, index) => (
            <div
              key={index}
              className={`file-item ${index === activeFileIndex ? 'active' : ''}`}
              onClick={() => handleFileSelect(index)}
            >
              <div className="file-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z" fill="currentColor"/>
                </svg>
              </div>
              <span className="file-name">{file.name}</span>
              <div className={`status-indicator ${getStageStatus(stage)}`}></div>
            </div>
          ))}
        </div>
      </div>

      {/* Pipeline Section */}
      <div className="sidebar-section">
        <div className="section-header">
          <h3>Pipeline</h3>
        </div>
        <div className="pipeline-timeline">
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
              <div
                key={stageKey}
                className={`pipeline-item ${stage === stageKey ? 'active' : ''} ${status}`}
                onClick={() => canNavigateToStage(stageKey) && setStage(stageKey)}
              >
                <div className="pipeline-indicator">
                  <div className={`status-dot ${status}`}></div>
                  <div className="pipeline-line"></div>
                </div>
                <div className="pipeline-content">
                  <span className="pipeline-name">{label}</span>
                  <span className="pipeline-status">{status}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>

    {/* Main Content Area */}
    <div className="main-content">
      {/* Header */}
      <div className="header">
        <div className="header-left">
          <div className="breadcrumb">
            <span className="breadcrumb-item">{projectSlug || 'Untitled'}</span>
            <span className="breadcrumb-separator">›</span>
            <span className="breadcrumb-item">
              {{
                [STAGES.UPLOAD]: "Upload",
                [STAGES.TRANSCRIPT]: "Transcript",
                [STAGES.ATOMS]: "Atomize",
                [STAGES.ANNOTATIONS]: "Annotate",
                [STAGES.GRAPH]: "Analyze",
                [STAGES.HUMAN_CHECKPOINTS]: "Review",
                [STAGES.BOARD]: "Visualize",
                [STAGES.QUALITY_GUARD]: "Validate",
                [STAGES.CHAT_ASSISTANT]: "Assist"
              }[stage] || "Unknown"}
            </span>
          </div>
        </div>
        <div className="header-right">
          {statusMessage && (
            <div className="status-indicator">
              <div className="status-spinner"></div>
              <span className="status-text">{statusMessage}</span>
            </div>
          )}
          <div className="header-actions">
            <button className="header-btn" title="Settings">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5 3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97 0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65A.588.588 0 0 0 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49 1.01c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1 0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.26 1.17-.59 1.69-.98l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66z" fill="currentColor"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="content-area">
        <div className="content-wrapper">
          {stage === STAGES.UPLOAD && (
            <UploadStage
              onFiles={handleFiles}
              projectSlug={projectSlug}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.TRANSCRIPT && (
            <TranscriptStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.ATOMS && (
            <AtomsStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.ANNOTATIONS && (
            <AnnotatedAtomsStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.GRAPH && (
            <GraphStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.HUMAN_CHECKPOINTS && (
            <HumanCheckpointsStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.BOARD && (
            <BoardStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.QUALITY_GUARD && (
            <QualityGuardStage
              file={files[activeFileIndex]}
              onStatusChange={setStatusMessage}
            />
          )}
          {stage === STAGES.CHAT_ASSISTANT && (
            <ChatAssistantStage
              file={files[activeFileIndex]}
              context={currentContext}
              onStatusChange={setStatusMessage}
            />
          )}
        </div>
      </div>
    </div>

    {/* Status Bar */}
    <div className="status-bar">
      <div className="status-left">
        <span className="status-item">
          <span className="status-icon">⚡</span>
          <span>Ready</span>
        </span>
      </div>
      <div className="status-right">
        <span className="status-item">{files.length} files</span>
        <span className="status-item">{stage >= STAGES.ATOMS ? 'Processing' : 'Idle'}</span>
      </div>
    </div>
  </div>
);
