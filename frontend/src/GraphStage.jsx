import { useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useGlobalStore } from "./store";
import "./GraphStage.css";

export default function GraphStage() {
  const activeFile = useGlobalStore((state) => state.activeFile);
  const graphs = useGlobalStore((state) => state.graphs);
  const localGraph = graphs?.[activeFile] || null;
  const graphRef = useRef();

  useEffect(() => {
    if (graphRef.current && localGraph?.nodes?.length > 0) {
      graphRef.current.zoomToFit(500); // fit animation in 500ms
    }
  }, [localGraph]);

  return (
    <div className="graph-container" style={{ width: "100%", height: "100vh", position: "relative" }}>
      <h2 style={{ padding: "1rem", fontSize: "1.25rem", color: "#00ffff" }}>Insights Graph</h2>

      {localGraph ? (
        <ForceGraph2D
          ref={graphRef}
          graphData={localGraph}
          nodeLabel="text"
          nodeAutoColorBy="speaker"
          linkDirectionalParticles={2}
          linkDirectionalArrowLength={4}
          linkCurvature={0.25}
          enableNodeDrag={true}
          backgroundColor="#000000"
        />
      ) : (
        <div style={{ color: "#ccc", padding: "2rem" }}>No graph data loaded.</div>
      )}
    </div>
  );
}
