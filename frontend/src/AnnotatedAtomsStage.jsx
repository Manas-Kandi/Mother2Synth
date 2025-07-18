import "./AnnotatedAtomsStage.css";

export default function AnnotatedAtomsStage({ annotatedAtoms }) {
  return (
    <section className="annotations-stage">
      <div className="annotations-container">
        <div className="annotations-content">
          {annotatedAtoms.map((atom, i) => (
            <div key={i} className="annotation-card">
              <header className="annotation-header">
                <span className="speaker">{atom.speaker}</span>
              </header>
              <p className="annotation-text">{atom.text}</p>
              <div className="annotation-tags">
                <span className="tag">Sentiment: {atom.sentiment}</span>
                <span className="tag">Speech Act: {atom.speech_act}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
