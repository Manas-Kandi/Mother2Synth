import { useState } from 'react';
import './App.css';

function App() {
  const [fileName, setFileName] = useState(null);

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
      setFileName(file.name);
      console.log('Dropped PDF:', file);
    } else {
      alert('Only PDF files are supported.');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setFileName(file.name);
      console.log('Selected PDF:', file);
    } else {
      alert('Only PDF files are supported.');
    }
  };

  return (
    <div
      className="drop-zone"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
    >
      <p>Drag and drop a PDF file here, or click to upload.</p>
      <input type="file" accept="application/pdf" onChange={handleFileChange} />
      {fileName && <p>Uploaded: {fileName}</p>}
    </div>
  );
}

export default App;
