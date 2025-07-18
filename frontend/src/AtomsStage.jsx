import "./AtomsStage.css";

export default function AtomsStage({ atoms }) {
  return (
    <section className="atoms-stage">
      <div className="atoms-container">
        <div className="atoms-content">
          {atoms.map((atom, i) => (
            <div key={i} className="atom-card">
              <header className="atom-header">
                <span className="speaker">{atom.speaker}</span>
                {/* Optional: Add a timestamp or identifier */}
                {/* <span className="timestamp">{formatTimestamp(atom.timestamp)}</span> */}
              </header>
              <p className="atom-text">{atom.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// Optional: Helper function to format timestamps
function formatTimestamp(timestamp) {
  const options = { year: 'numeric', month: 'short', day: 'numeric' };
  return new Date(timestamp).toLocaleDateString(undefined, options);
}
