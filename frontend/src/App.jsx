import { useState } from 'react';

function App() {
  const [fileNames, setFileNames] = useState([]);

  const handleFiles = (files) => {
    const validPdfs = Array.from(files).filter(file => file.type === 'application/pdf');

    if (validPdfs.length === 0) {
      alert('Please upload at least one PDF file.');
      return;
    }

    const newNames = validPdfs.map(file => file.name);
    setFileNames(prev => [...prev, ...newNames]);
  };

  const handleChange = (e) => {
    handleFiles(e.target.files);
  };

  return (
    <div style={{ padding: '2rem', color: '#fff' }}>
      <input
        type="file"
        accept="application/pdf"
        onChange={handleChange}
        multiple
      />
      {fileNames.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <p>Uploaded PDFs:</p>
          <ul>
            {fileNames.map((name, index) => (
              <li key={index}>{name}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
