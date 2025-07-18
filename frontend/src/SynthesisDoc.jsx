import "./SynthesisDoc.css";

export default function SynthesisDoc({ cleaned, atoms, annotated }) {
  return (
    <article className="synth-doc">
      {/* Section 1 – Cleaned Transcript */}
      <section className="transcript">
        {cleaned.split("\n\n").map((block, i) => {
          const [speaker, ...rest] = block.split(": ");
          return (
            <p key={i}>
              <strong>{speaker}:</strong> {rest.join(": ")}
            </p>
          );
        })}
      </section>

      {/* Section 2 – Atomized Units */}
      <section className="atoms">
        {atoms.map((a, i) => (
          <p key={i}>{a.text}</p>
        ))}
      </section>

      {/* Section 3 – Annotated Atoms */}
      <section className="annotated">
        {annotated.map((a, i) => (
          <div key={i} className="annotated-unit">
            <p>{a.text}</p>
            <aside>
              {a.speaker} · {a.speech_act} · {a.sentiment}
            </aside>
          </div>
        ))}
      </section>
    </article>
  );
}
