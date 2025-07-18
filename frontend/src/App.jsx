import { useState } from 'react';
import PipelineDashboard from "./PipelineDashboard";

function App() {
  const [pdfFiles, setPdfFiles] = useState([]);

  const handleFiles = (files) => {
    const validPdfs = Array.from(files).filter(f => f.type === 'application/pdf');
    setPdfFiles(validPdfs);
  };

  const handleChange = (e) => {
    handleFiles(e.target.files);
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
          <PipelineDashboard files={pdfFiles} />
        </>
      )}
    </div>
  );
}

export default App;
