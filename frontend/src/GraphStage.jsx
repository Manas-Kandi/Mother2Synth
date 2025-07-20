import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useGlobalStore } from "./store";
import "./GraphStage.css";

export default function GraphStage() {
  const activeFile = useGlobalStore((state) => state.activeFile);
  const graphs = useGlobalStore((state) => state.graphs);
  const localGraph = graphs?.[activeFile] || null;
  const graphRef = useRef();
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    if (graphRef.current && localGraph?.nodes?.length > 0) {
      graphRef.current.zoomToFit(500);
    }
  }, [localGraph]);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  // Get connected nodes for selected node
  const getConnectedNodes = (nodeId) => {
    if (!localGraph) return [];
    return localGraph.links
      .filter((link) => link.source === nodeId || link.target === nodeId)
      .map((link) => {
        const connectedId = link.source === nodeId ? link.target : link.source;
        return localGraph.nodes.find((n) => n.id === connectedId);
      })
      .filter(Boolean);
  };

  return (
    <div className="graph-container">
      <h2 style={{ padding: "1rem", fontSize: "1.25rem", color: "#00ffff" }}>
        Insights Graph
      </h2>

      {localGraph ? (
        <>
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
            nodeVal={(node) => {
              const connections = localGraph.links.filter(
                (link) => link.source === node.id || link.target === node.id
              ).length;
              return Math.max(4, connections * 2);
            }}
            onNodeClick={handleNodeClick}
          />

          {/* Details Panel */}
          {selectedNode && (
            <div className="details-panel">
              <div className="panel-header">
                <h3>Node Details</h3>
                <button
                  className="close-btn"
                  onClick={() => setSelectedNode(null)}
                >
                  ×
                </button>
              </div>

              <div className="panel-content">
                <div className="main-text">{selectedNode.text}</div>

                <div className="node-meta">
                  <span className="speaker">{selectedNode.speaker}</span>
                  <span className="sentiment">{selectedNode.sentiment}</span>
                </div>

                <div className="connections">
                  <h4>
                    Connected to (
                    {getConnectedNodes(selectedNode.id).length})
                  </h4>
                  {getConnectedNodes(selectedNode.id).map((node) => (
                    <div key={node.id} className="connected-item">
                      {node.text?.substring(0, 60)}...
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div style={{ color: "#ccc", padding: "2rem" }}>
          No graph data loaded.
        </div>
      )}
    </div>
  );
}