import { useState } from 'react';

function App() {
  const [pdfFiles, setPdfFiles] = useState([]);
  const [responseMessage, setResponseMessage] = useState(null);

  const handleFiles = (files) => {
    const validPdfs = Array.from(files).filter(f => f.type === 'application/pdf');
    setPdfFiles(validPdfs);
  };

  const handleChange = (e) => {
    handleFiles(e.target.files);
  };

  const uploadFiles = async () => {
    if (pdfFiles.length === 0) {
      alert("No files selected.");
      return;
    }

    const formData = new FormData();
    pdfFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const res = await fetch("http://localhost:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("Server response:", data);
      setResponseMessage(data.message);
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Something went wrong during upload.");
    }
  };

  return (
    <div style={{ padding: '2rem', color: '#fff' }}>
      <input
        type="file"
        accept="application/pdf"
        multiple
        onChange={handleChange}
      />
      {pdfFiles.length > 0 && (
        <>
          <ul style={{ marginTop: '1rem' }}>
            {pdfFiles.map((f, i) => (
              <li key={i}>{f.name}</li>
            ))}
          </ul>
          <button
            onClick={uploadFiles}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem' }}
          >
            Upload PDFs
          </button>
        </>
      )}
      {responseMessage && (
        <p style={{ marginTop: '1rem', color: 'lightgreen' }}>{responseMessage}</p>
      )}
    </div>
  );
}

export default App;
