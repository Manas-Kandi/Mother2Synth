import "./AnnotatedAtomsStage.css";

export default function AnnotatedAtomsStage({ file }) {
  if (!file || !file.annotated || file.annotated.length === 0) {
    return <p className="loading">No annotated atoms available.</p>;
  }

  return (
    <section className="annotations-stage">
      <h2 className="annotations-header">{file.name}</h2>
      <div className="annotations-scroll">
        {file.annotated.map((atom, i) => (
          <div key={atom.id || i} className="annotation-card">
            <header className="annotation-meta">
              <span className="speaker">{atom.speaker}</span>
              <span className="tag">Speech Act: {atom.speech_act}</span>
              <span className="tag">Sentiment: {atom.sentiment}</span>
              <span className="source-label">{atom.source_file}</span>
            </header>
            <p className="annotation-text">{atom.text}</p>
            {atom.insights && atom.insights.length > 0 && (
              <ul className="insights-list">
                {atom.insights.map((insight, idx) => (
                  <li key={idx}>
                    {insight.type}: <strong>{insight.label}</strong> ({insight.weight})
                  </li>
                ))}
              </ul>
            )}
            {atom.tags && atom.tags.length > 0 && (
              <p className="tag-line">Tags: {atom.tags.join(", ")}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
