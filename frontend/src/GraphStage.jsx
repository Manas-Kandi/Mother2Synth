import { useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useGlobalStore } from "./store";
import "./GraphStage.css";

export default function GraphStage() {
  const graphRef = useRef();
  const selectedFile = useGlobalStore((state) => state.selectedFile);
  const graph = useGlobalStore((state) =>
    selectedFile ? state.graph[selectedFile] : null
  );

  useEffect(() => {
    if (!graphRef.current || !graph) return;
    graphRef.current.d3Force("charge").strength(-120);
    graphRef.current.d3Force("link").distance(160);
  }, [graph]);

  if (!graph || !graph.nodes?.length) {
    return <div className="p-8 text-center text-gray-500">No graph yet</div>;
  }

  return (
    <div className="w-full h-screen">
      <ForceGraph2D
        ref={graphRef}
        graphData={graph}
        nodeLabel={(node) => node.text || node.id}
        nodeAutoColorBy="source_file"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label =
            node.text.slice(0, 60) +
            (node.text.length > 60 ? "..." : "");
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Inter`;
          ctx.fillStyle = node.color || "white";
          ctx.beginPath();
          ctx.arc(node.x, node.y, 6, 0, 2 * Math.PI, false);
          ctx.fill();
          ctx.fillStyle = "#ddd";
          ctx.fillText(label, node.x + 8, node.y + 3);
        }}
        linkColor={() => "#888"}
        linkWidth={1}
        width={window.innerWidth - 300}
        height={window.innerHeight - 50}
      />
    </div>
  );
}
