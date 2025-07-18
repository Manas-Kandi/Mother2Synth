import "./TranscriptStage.css";

export default function TranscriptStage({ transcript }) {
  if (!transcript) return null;

  // Split on lines that start with a speaker label, like "Interviewer:" or "Participant:"
  const speakerBlocks = transcript.split(/(?=[A-Z][a-z]+(?:\s\[inferred\])?:)/g);

  return (
    <section className="transcript-stage">
      <div className="transcript-scroll">
        {speakerBlocks.map((block, i) => {
          const [speakerPart, ...textParts] = block.split(":");
          const speaker = speakerPart?.trim();
          const text = textParts.join(":").trim();

          if (!speaker || !text) return null;

          return (
            <div key={i} className="speaker-block">
              <div className="speaker-name">{speaker}</div>
              <p className="speaker-text">{text}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
