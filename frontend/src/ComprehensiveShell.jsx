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
      board: activeFile?.board || {}
    });
  }, [projectSlug, files, activeFileIndex, stage]);

  useEffect(() => {
    updateContext();
  }, [updateContext]);

  async function handleFiles(selectedFiles, slug) {
    console.log('handleFiles called with:', { selectedFiles, slug });
    
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

    // Set project slug immediately for UI feedback
    setProjectSlug(slug);
    setStatusMessage(`Preparing to process ${selectedFiles.length} file(s)...`);

    // Validate project (but don't block if it fails)
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
      // Continue with upload even if validation fails
    }

    const updated = [];
    let encounteredError = false;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const filename = file.name;
      
      try {
        // Step 1: Upload file
        setStatusMessage(`Uploading: ${filename} (${i+1}/${selectedFiles.length})`);
        console.log(`Processing file ${i+1}/${selectedFiles.length}:`, filename);
        
        // Create form data
        const form = new FormData();
        form.append("files", file);  // Use "files" to match backend endpoint parameter
        
        console.log('Uploading file to server...');
        const uploadRes = await fetchWithProject(
          "/upload", 
          {
            method: "POST",
            body: form,
            // Let the browser set Content-Type with boundary
          }, 
          slug
        );
        
        if (!uploadRes.ok) {
          const errorText = await uploadRes.text().catch(() => 'No error details');
          console.error('Upload failed:', uploadRes.status, errorText);
          throw new Error(`Upload failed (${uploadRes.status}): ${errorText}`);
        }
        
        console.log('File uploaded successfully, normalizing...');
        setStatusMessage(`Normalizing: ${filename} (${i+1}/${selectedFiles.length})`);

        // Step 2: Normalize
        console.log('Normalizing file...');
        const normRes = await fetchWithProject(
          `/normalize/${encodeURIComponent(filename)}`, 
          { method: "GET" }, 
          slug
        );
        
        if (!normRes.ok) {
          const errorText = await normRes.text().catch(() => 'No error details');
          throw new Error(`Normalization failed (${normRes.status}): ${errorText}`);
        }
        
        const normData = await normRes.json();
        const cleaned = normData.content;
        console.log('File normalized successfully');

        // Step 3: Atomize
        setStatusMessage(`Processing: ${filename} (${i+1}/${selectedFiles.length})`);
        console.log('Atomizing content...');
        const atomRes = await fetchWithProject(
          `/atomise/${encodeURIComponent(filename)}`, 
          { method: "GET" }, 
          slug
        );
        
        if (!atomRes.ok) {
          const errorText = await atomRes.text().catch(() => 'No error details');
          throw new Error(`Atomization failed (${atomRes.status}): ${errorText}`);
        }
        
        const { atoms } = await atomRes.json();
        console.log('Content atomized successfully');

        // Step 4: Annotate
        setStatusMessage(`Analyzing: ${filename} (${i+1}/${selectedFiles.length})`);
        console.log('Annotating atoms...');
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
          const errorText = await annotateRes.text().catch(() => 'No error details');
          throw new Error(`Annotation failed (${annotateRes.status}): ${errorText}`);
        }
        
        const annotated = await annotateRes.json();
        console.log('Atoms annotated successfully');

        // Step 5: Build graph
        setStatusMessage(`Building insights: ${filename} (${i+1}/${selectedFiles.length})`);
        console.log('Building graph...');
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
          const errorText = await graphRes.text().catch(() => 'No error details');
          throw new Error(`Graph build failed (${graphRes.status}): ${errorText}`);
        }
        
        const graph = await graphRes.json();
        console.log('Graph built successfully');

        // Step 6: Create board
        setStatusMessage(`Finalizing: ${filename} (${i+1}/${selectedFiles.length})`);
        console.log('Creating board...');
        const boardRes = await fetchWithProject(
          "/board/create", 
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
              atoms: annotated, 
              themes: graph.themes, 
              project_slug: slug, 
              filename 
            }),
          }, 
          slug
        );
        
        if (!boardRes.ok) {
          const errorText = await boardRes.text().catch(() => 'No error details');
          throw new Error(`Board creation failed (${boardRes.status}): ${errorText}`);
        }
        
        const board = await boardRes.json();
        console.log('Board created successfully');

        // Add to processed files
        const fileData = {
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
        
        updated.push(fileData);
        console.log('File processing complete:', fileData);
      } catch (error) {
        console.error(`Error processing ${selectedFiles[i]?.name}:`, error);
        encounteredError = true;
        setStatusMessage(`Error processing ${selectedFiles[i]?.name || 'unknown'}: ${error.message}`);
        updated.push({
          name: selectedFiles[i]?.name || 'unknown',
          status: 'error',
          error: error.message
        });
      }
    }

    const newFiles = [...files, ...updated];
    setFiles(newFiles);
    if (!encounteredError) {
      setActiveFileIndex(newFiles.length - updated.length);
      setSelectedFile(newFiles[newFiles.length - updated.length]?.name || null);
      setStage(STAGES.TRANSCRIPT);
      setStatusMessage("Processing complete!");
    }
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
