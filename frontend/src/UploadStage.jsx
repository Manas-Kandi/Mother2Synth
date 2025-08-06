import { useEffect, useState } from "react";
import { useGlobalStore } from "./store";
import { fetchWithProject } from "./api";
import "./UploadStage.css";

const TrashIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
  >
    <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14zM10 11v6M14 11v6" />
  </svg>
);

export default function UploadStage({
  onFiles,
  statusMessage,
  onJump,
}) {
  const [projects, setProjects] = useState({});
  const { projectSlug, setProjectSlug } = useGlobalStore((state) => state);
  const isUploadDisabled = !projectSlug || projectSlug.trim() === '';

  useEffect(() => {
    fetchWithProject("/projects", {}, projectSlug)
      .then((r) => r.json())
      .then(setProjects)
      .catch(console.error);
  }, [projectSlug]);


  const [isDragging, setIsDragging] = useState(false);

  const handleChange = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = Array.from(e.target.files || []).filter(f => f.type === "application/pdf");
    console.log('Files selected:', files);
    
    if (!files.length) {
      console.warn('No valid PDF files selected');
      return;
    }
    
    if (!projectSlug) {
      console.warn('Cannot upload: No project slug provided');
      setStatusMessage('Please enter a project slug first');
      return;
    }
    
    try {
      console.log('Calling onFiles with:', { files, projectSlug });
      onFiles(files, projectSlug);
      // Reset the input to allow selecting the same file again if needed
      e.target.value = '';
    } catch (error) {
      console.error('Error processing files:', error);
      setStatusMessage(`Error: ${error.message}`);
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isUploadDisabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isUploadDisabled) {
      e.dataTransfer.dropEffect = 'copy';
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (isUploadDisabled) {
      console.warn('Upload is disabled - missing project slug');
      setStatusMessage('Please enter a project slug first');
      return;
    }
    
    const files = Array.from(e.dataTransfer.files || []).filter(f => f.type === "application/pdf");
    console.log('Files dropped:', files);
    
    if (!files.length) {
      console.warn('No PDF files found in drop');
      setStatusMessage('Please drop PDF files only');
      return;
    }
    
    try {
      console.log('Calling onFiles with:', { files, projectSlug });
      onFiles(files, projectSlug);
    } catch (error) {
      console.error('Error processing dropped files:', error);
      setStatusMessage(`Error: ${error.message}`);
    }
  };

  return (
    <main className="upload-wrapper">
      <section className="upload-box">
        <h1>Start or Resume</h1>

        {/* NEW: project list */}
        {Object.keys(projects).length > 0 && (
          <>
            <h2>Existing Projects</h2>
            <ul className="project-list">
              {Object.entries(projects).map(([name, flags]) => (
                <li key={name}>
                  <button
                    className="jump-link"
                    onClick={() => {
                      setProjectSlug(name);
                      if (onJump) onJump(name);
                    }}
                  >
                    {name}
                  </button>
                  <div className="flags">
                    {Object.entries(flags).map(([k, v]) => (
                      <span key={k} className={v ? "done" : "pending"}>
                        {k}
                      </span>
                    ))}
                  </div>
                  <button
                    className="delete-btn"
                    onClick={async () => {
                      await fetchWithProject(
                        `/projects/${encodeURIComponent(name)}`,
                        {
                          method: "DELETE",
                        },
                        projectSlug
                      );
                      // refresh list
                      fetchWithProject("/projects", {}, projectSlug)
                        .then((r) => r.json())
                        .then(setProjects);
                    }}
                    title="Delete project"
                  >
                    <TrashIcon />
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <input
          type="text"
          value={projectSlug}
          onChange={(e) => setProjectSlug(e.target.value)}
          placeholder="Enter project slug"
          className="slug-input"
          aria-label="Project slug"
        />

        <div className="upload-container">
          <input
            type="file"
            accept="application/pdf"
            multiple
            onChange={handleChange}
            id="file-upload"
            disabled={isUploadDisabled}
            className="visually-hidden"
          />
          <label
            htmlFor="file-upload"
            className={`upload-area ${isUploadDisabled ? 'disabled' : ''} ${isDragging ? 'drag-active' : ''}`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            aria-disabled={isUploadDisabled}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                document.getElementById('file-upload')?.click();
              }
            }}
          >
            <div className="upload-content">
              <div className="upload-icon">📁</div>
              <div>Drop PDFs here or click to select files</div>
              <div className="upload-hint">Supports multiple PDF files</div>
            </div>
          </label>
        </div>


        {statusMessage && (
          <p className="status-message">
            <span className="dot"></span> {statusMessage}
          </p>
        )}
      </section>
    </main>
  );
}
