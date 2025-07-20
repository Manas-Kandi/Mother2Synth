import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import "./GraphStage.css";

export default function GraphStage({ file }) {
  // DEBUG: Let's see what we're getting
  console.log("🔍 GraphStage Debug:");
  console.log("- file:", file);
  console.log("- file?.graph:", file?.graph);
  console.log("- nodes length:", file?.graph?.nodes?.length);
  console.log("- edges length:", file?.graph?.edges?.length);

  const [selectedNode, setSelectedNode] = useState(null);
  const [filters, setFilters] = useState({
    speaker: 'all',
    sentiment: 'all',
    confidence: 'all'
  });
  const graphRef = useRef();

  // Get graph data from file prop (consistent with other stages)
  const graphData = file?.graph || null;

  useEffect(() => {
    if (graphRef.current && graphData?.nodes?.length > 0) {
      // Auto-fit the graph when data loads
      setTimeout(() => {
        graphRef.current.zoomToFit(400, 50);
      }, 100);
    }
  }, [graphData]);

  if (!file || !graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="graph-stage">
        <div className="empty-state">
          <div className="empty-icon">🕸️</div>
          <h2 className="empty-title">No graph data available</h2>
          <p className="empty-text">The insights graph will appear here after analysis is complete</p>
        </div>
      </div>
    );
  }

  // Filter nodes and edges based on current filters
  const filteredData = filterGraphData(graphData, filters);
  
  // Get unique values for filter options
  const speakers = [...new Set(graphData.nodes.map(n => n.speaker))].filter(Boolean);
  const sentiments = [...new Set(graphData.nodes.map(n => n.sentiment))].filter(Boolean);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  const handleFilterChange = (type, value) => {
    setFilters(prev => ({ ...prev, [type]: value }));
  };

  return (
    <div className="graph-stage">
      <div className="graph-document">
        <div className="document-header">
          <h1 className="document-title">Insights Graph</h1>
          <p className="document-subtitle">{file.name.replace('.pdf', '')}</p>
          <div className="document-meta">
            {filteredData.nodes.length} insights · {filteredData.edges.length} connections
          </div>
        </div>

        <div className="graph-controls">
          <div className="filter-group">
            <label className="filter-label">Speaker</label>
            <select 
              className="filter-select"
              value={filters.speaker}
              onChange={(e) => handleFilterChange('speaker', e.target.value)}
            >
              <option value="all">All Speakers</option>
              {speakers.map(speaker => (
                <option key={speaker} value={speaker}>{speaker}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Sentiment</label>
            <select 
              className="filter-select"
              value={filters.sentiment}
              onChange={(e) => handleFilterChange('sentiment', e.target.value)}
            >
              <option value="all">All Sentiments</option>
              {sentiments.map(sentiment => (
                <option key={sentiment} value={sentiment}>{sentiment}</option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label className="filter-label">Confidence</label>
            <select 
              className="filter-select"
              value={filters.confidence}
              onChange={(e) => handleFilterChange('confidence', e.target.value)}
            >
              <option value="all">All Confidence</option>
              <option value="high">High Confidence</option>
              <option value="medium">Medium Confidence</option>
              <option value="low">Low Confidence</option>
            </select>
          </div>
        </div>

        <div className="graph-container">
          <ForceGraph2D
            ref={graphRef}
            graphData={{
              nodes: filteredData.nodes,
              links: filteredData.edges  // ForceGraph2D expects 'links', not 'edges'
            }}
            nodeLabel={(node) => `${node.speaker}: ${node.text?.substring(0, 100)}...`}
            nodeColor={(node) => getNodeColor(node)}
            nodeRelSize={6}
            linkColor={() => 'rgba(10, 255, 255, 0.3)'}
            linkWidth={(link) => Math.sqrt(link.weight || 1) * 2}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.1}
            enableNodeDrag={true}
            enableZoom={true}
            enablePan={true}
            backgroundColor="#0a0a0a"
            onNodeClick={handleNodeClick}
            onBackgroundClick={() => setSelectedNode(null)} // Clear selection when clicking background
            nodeCanvasObject={(node, ctx, globalScale) => {
              drawCustomNode(node, ctx, globalScale);
            }}
          />
        </div>

        {selectedNode && (
          <div className="node-details">
            <div className="node-details-header">
              <h3 className="node-title">Selected Insight</h3>
              <button 
                className="close-details"
                onClick={() => setSelectedNode(null)}
              >
                ×
              </button>
            </div>
            <div className="node-content">
              <div className="node-speaker">
                <span className="node-speaker-label">{selectedNode.speaker}</span>
                {selectedNode.sentiment && (
                  <span className={`sentiment-badge sentiment-${selectedNode.sentiment?.toLowerCase()}`}>
                    {selectedNode.sentiment}
                  </span>
                )}
              </div>
              <p className="node-text">{selectedNode.text}</p>
              {selectedNode.insights && selectedNode.insights.length > 0 && (
                <div className="node-insights">
                  <h4 className="insights-title">Insights</h4>
                  {selectedNode.insights.map((insight, i) => (
                    <div key={i} className="insight-tag">
                      <span className="insight-type">{insight.type}</span>
                      <span className="insight-label">{insight.label}</span>
                      <span className="insight-weight">({insight.weight})</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper functions
function filterGraphData(graphData, filters) {
  let filteredNodes = graphData.nodes;

  if (filters.speaker !== 'all') {
    filteredNodes = filteredNodes.filter(node => node.speaker === filters.speaker);
  }

  if (filters.sentiment !== 'all') {
    filteredNodes = filteredNodes.filter(node => node.sentiment === filters.sentiment);
  }

  if (filters.confidence !== 'all') {
    filteredNodes = filteredNodes.filter(node => node.confidence === filters.confidence);
  }

  // Filter edges to only include connections between visible nodes
  const nodeIds = new Set(filteredNodes.map(n => n.id));
  const filteredEdges = graphData.edges.filter(edge => 
    nodeIds.has(edge.source) && nodeIds.has(edge.target)
  );

  return {
    nodes: filteredNodes,
    edges: filteredEdges
  };
}

function getNodeColor(node) {
  // Color by sentiment
  switch (node.sentiment?.toLowerCase()) {
    case 'positive': return '#10b981';
    case 'negative': return '#ef4444';
    case 'neutral': return '#6b7280';
    default: return '#0affff';
  }
}

function drawCustomNode(node, ctx, globalScale) {
  const label = node.speaker || '';
  const fontSize = 12 / globalScale;
  const radius = 6;

  // Draw node circle
  ctx.beginPath();
  ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
  ctx.fillStyle = getNodeColor(node);
  ctx.fill();

  // Draw border
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.lineWidth = 1 / globalScale;
  ctx.stroke();

  // Draw label if zoomed in enough
  if (globalScale > 1) {
    ctx.font = `${fontSize}px Inter, sans-serif`;
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText(label, node.x, node.y + radius + 2);
  }
}