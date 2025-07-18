import "./UploadStage.css";

export default function UploadStage({ onFiles, statusMessage }) {
  function handleChange(e) {
    const files = Array.from(e.target.files || []);
    if (files.length) onFiles(files);
  }

  return (
    <main className="upload-wrapper">
      <section className="upload-box">
        <h1>Start Synthesizing</h1>
        <p>Drop a PDF transcript to begin the pipeline.</p>
        <label htmlFor="file-upload" className="upload-area">
          Drop PDFs here or click to select
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
