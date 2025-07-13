import { useState } from 'react';

function App() {
  const [pdfFiles, setPdfFiles] = useState([]);
  const [responseMessage, setResponseMessage] = useState(null);
  const [atoms, setAtoms] = useState([]);
  const [atomFile, setAtomFile] = useState(null); // for saving atoms.json

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
      setResponseMessage(data.message);
      // Chain GET /atomise after upload
      fetchAtoms();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("Something went wrong during upload.");
    }
  };

  const fetchAtoms = async () => {
    try {
      const res = await fetch("http://localhost:8000/atomise");
      const data = await res.json();
      // Flatten all atoms from all files into a single array for display
      const allAtoms = Object.values(data).flat();
      setAtoms(allAtoms);
      // Save atoms.json for next agents
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      setAtomFile(window.URL.createObjectURL(blob));
    } catch (err) {
      console.error("Failed to fetch atomised data:", err);
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
      {atoms.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h3>Atomised Ideas</h3>
          {atoms.map((atom, i) => (
            <div key={i} className="mb-4 p-2 border rounded" style={{ background: '#222', marginBottom: '1rem', padding: '1rem', borderRadius: '8px', border: '1px solid #444' }}>
              <strong>{atom.speaker}:</strong> {atom.text}
            </div>
          ))}
          {atomFile && (
            <a href={atomFile} download="atoms.json" style={{ color: '#0ff', textDecoration: 'underline' }}>
              Download atoms.json
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
