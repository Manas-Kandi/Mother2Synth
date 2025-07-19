import "./GraphStage.css";

export default function GraphStage({ graph }) {
  if (!graph || !graph.nodes) return <p>No graph yet</p>;
  return (
    <section className="graph-stage">
      <h2>Research Graph</h2>
      <div className="graph-scroll">
        <h3>Nodes ({graph.nodes.length})</h3>
        <ul>
          {graph.nodes.map((n) => (
            <li key={n.id}>{n.speaker}: {n.text.slice(0, 60)}…</li>
          ))}
        </ul>
        <h3>Edges ({graph.edges.length})</h3>
        <ul>
          {graph.edges.map((e) => (
            <li key={e.source + e.target}>
              {e.source} → {e.target} ({e.type}: {e.label})
            </li>
          ))}
        </ul>
        {graph.edges.length === 0 && graph.edges_note && (
          <p className="empty-note">{graph.edges_note}</p>
        )}
      </div>
    </section>
  );
}
