import "./TranscriptStage.css";

export default function TranscriptStage({ transcript }) {
  if (!transcript) return null;

  // 1️⃣  Regex: grab speaker + everything until next speaker or EOF
  const SPEAKER_RE = /(Speaker\s*\d+|Interviewer|Participant)\s*:?\s*(.*?)(?=(?:\n(?:Speaker|Interviewer|Participant)|$))/gis;

  const blocks = [];
  let match;
  while ((match = SPEAKER_RE.exec(transcript)) !== null) {
    const speaker = match[1].trim();
    const text    = match[2].trim();
    if (text) blocks.push({ speaker, text });
  }

  return (
    <section className="transcript-stage">
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
