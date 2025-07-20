import "./TranscriptStage.css";

export default function TranscriptStage({ file }) {
  if (!file || !file.cleaned) return <p className="loading">No transcript loaded.</p>;

  const transcript = file.cleaned;

  // 1️⃣ Regex to extract speaker blocks
  const SPEAKER_RE = /(Speaker\s*\d+|Interviewer|Participant|[A-Z][a-z]+(?:\s\[inferred\])?):\s*(.*?)(?=(?:\n(?:[A-Z][a-z]+|Speaker|Participant|Interviewer)|$))/gis;

  const blocks = [];
  let match;
  while ((match = SPEAKER_RE.exec(transcript)) !== null) {
    const speaker = match[1].trim();
    const text = match[2].trim();
    if (text) blocks.push({ speaker, text });
  }

  return (
    <section className="transcript-stage">
      <h2 className="transcript-header">{file.name}</h2>
      <div className="transcript-scroll">
        {blocks.map((b, i) => (
          <div key={i} className="speaker-block">
            <div className="speaker-name">{b.speaker}</div>
            <p className="speaker-text">{b.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
