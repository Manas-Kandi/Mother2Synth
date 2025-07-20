import "./AtomsStage.css";

export default function AtomsStage({ file }) {
  if (!file || !file.atoms || file.atoms.length === 0) {
    return <p className="loading">No atoms for this document yet.</p>;
  }

  return (
    <section className="atoms-stage">
      <h2 className="atoms-header">{file.name}</h2>
      <div className="atoms-scroll">
        {file.atoms.map((atom, i) => (
          <div key={atom.id || i} className="atom-card">
            <div className="atom-meta">
              <span className="speaker-label">{atom.speaker}</span>
              <span className="source-label">{atom.source_file}</span>
            </div>
            <p className="atom-text">{atom.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
