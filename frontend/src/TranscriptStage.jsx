import "./TranscriptStage.css";

export default function TranscriptStage({ transcript }) {
  return (
    <section className="transcript-stage">
      <div className="transcript-content">
        {transcript.split("\n\n").map((block, i) => {
          const [speaker, ...rest] = block.split(": ");
          return (
            <div key={i} className="transcript-block">
              <h4 className="speaker">{speaker.trim()}</h4>
              <p>{rest.join(": ").trim()}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
