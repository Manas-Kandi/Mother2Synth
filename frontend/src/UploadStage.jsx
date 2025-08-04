import { useEffect, useState } from "react";
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
  projectSlug,
  setProjectSlug,
  onJump,
}) {
  const [projects, setProjects] = useState({});
  const [slugValid, setSlugValid] = useState(false);

  useEffect(() => {
    fetchWithProject("/projects")
      .then((r) => r.json())
      .then(setProjects);
  }, []);

  useEffect(() => {
    if (projectSlug) {
      setSlugValid(Object.prototype.hasOwnProperty.call(projects, projectSlug));
    } else {
      setSlugValid(false);
    }
  }, [projectSlug, projects]);

  function handleChange(e) {
    const files = Array.from(e.target.files || []);
    if (files.length && slugValid) onFiles(files, projectSlug);
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
                        }
                      );
                      // refresh list
                      fetchWithProject("/projects")
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
          className={`slug-input ${projectSlug && !slugValid ? "invalid" : ""}`}
        />
        {projectSlug && !slugValid && (
          <p className="slug-error">Project slug not found</p>
        )}

        <label
          htmlFor="file-upload"
          className={`upload-area ${slugValid ? "" : "disabled"}`}
        >
          Drop new PDFs here or click to select
        </label>
        <input
          type="file"
          accept="application/pdf"
          multiple
          onChange={handleChange}
          id="file-upload"
          disabled={!slugValid}
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
