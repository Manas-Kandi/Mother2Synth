import { useEffect, useState } from "react";
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

export default function UploadStage({ onFiles, statusMessage, onJump }) {
  const [projects, setProjects] = useState({});

  useEffect(() => {
    fetch("http://localhost:8000/projects")
      .then((r) => r.json())
      .then(setProjects);
  }, []);

  function handleChange(e) {
    const files = Array.from(e.target.files || []);
    if (files.length) onFiles(files);
  }

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
                    onClick={() => onJump && onJump(name)}
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
                      await fetch(
                        `http://localhost:8000/projects/${encodeURIComponent(name)}`,
                        {
                          method: "DELETE",
                        }
                      );
                      // refresh list
                      fetch("http://localhost:8000/projects")
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

        <label htmlFor="file-upload" className="upload-area">
          Drop new PDFs here or click to select
        </label>
        <input
          type="file"
          accept="application/pdf"
          multiple
          onChange={handleChange}
          id="file-upload"
        />

        {statusMessage && (
          <p className="status-message">
            <span className="dot"></span> {statusMessage}
          </p>
        )}
      </section>
    </main>
  );
}
