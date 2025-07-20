// Fixed GraphStage.jsx with proper data validation

import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useGlobalStore } from "./store";
import "./GraphStage.css";

export default function GraphStage({ file }) {
  const graphRef = useRef();
  const [selectedNode, setSelectedNode] = useState(null);
  
  // Validate and format graph data
  const formatGraphData = (rawGraph) => {
    if (!rawGraph) return null;
    
    // Map edges to links (ForceGraph2D expects 'links', not 'edges')
    const nodes = Array.isArray(rawGraph.nodes) ? rawGraph.nodes : [];
    const edges = Array.isArray(rawGraph.edges) ? rawGraph.edges : 
                  Array.isArray(rawGraph.links) ? rawGraph.links : [];
    
    console.log("Raw edges:", edges.slice(0, 3)); // Show first 3 edges
    
    // Validate that nodes have required properties
    const validNodes = nodes.filter(node => 
      node && typeof node === 'object' && node.id !== undefined
    );
    
    // Create set of node IDs for validation
    const nodeIds = new Set(validNodes.map(n => n.id));
    console.log("Valid node IDs:", Array.from(nodeIds).slice(0, 5)); // Show first 5 node IDs
    
    // Validate that links reference existing nodes
    const validLinks = edges.filter(link => {
      const hasValidStructure = link && typeof link === 'object';
      
      // Handle both string IDs and object references
      let sourceId, targetId;
      if (typeof link.source === 'object') {
        sourceId = link.source.id;
      } else {
        sourceId = link.source;
      }
      
      if (typeof link.target === 'object') {
        targetId = link.target.id;
      } else {
        targetId = link.target;
      }
      
      const hasSource = nodeIds.has(sourceId);
      const hasTarget = nodeIds.has(targetId);
      
      if (!hasValidStructure) console.log("Invalid link structure:", link);
      if (!hasSource) console.log("Invalid source ID:", sourceId, "not in nodeIds");
      if (!hasTarget) console.log("Invalid target ID:", targetId, "not in nodeIds");
      
      return hasValidStructure && hasSource && hasTarget;
    });
    
    console.log("Valid links after filtering:", validLinks.length);
    
    return {
      nodes: validNodes,
      links: validLinks  // Always return as 'links' for ForceGraph2D
    };
  };
  
  // Enhanced graph data with LLM-powered styling
  const [styledGraph, setStyledGraph] = useState(null);
  const [isEnhancing, setIsEnhancing] = useState(false);
  
  const enhanceGraphWithLLM = async (rawGraph) => {
    if (!rawGraph || !rawGraph.nodes) return null;
    
    try {
      console.log("Enhancing graph with LLM...", rawGraph.nodes.length, "nodes");
      
      // Send nodes to backend for LLM analysis
      const response = await fetch('http://localhost:8000/enhance-graph', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nodes: rawGraph.nodes.map(node => ({
            id: node.id,
            text: node.text,
            speaker: node.speaker,
            insights: node.insights || [],
            tags: node.tags || []
          }))
        })
      });
      
      if (!response.ok) {
        console.warn('LLM enhancement failed, using original data');
        return rawGraph;
      }
      
      const enhanced = await response.json();
      console.log("LLM enhancement received:", enhanced);
      console.log("Sample enhanced node:", enhanced[0]);
      
      // Merge enhanced styling back into original graph
      const enhancedNodes = rawGraph.nodes.map(node => {
        const styling = enhanced.find(s => s.id === node.id);
        console.log(`Styling for node ${node.id}:`, styling);
        return {
          ...node,
          nodeColor: styling?.color || '#666666',
          nodeIcon: styling?.icon || '•',
          nodeLabel: styling?.label || 'insight',
          category: styling?.category || 'other'
        };
      });
      
      console.log("Sample enhanced node after merging:", enhancedNodes[0]);
      
      return {
        ...rawGraph,
        nodes: enhancedNodes
      };
      
    } catch (error) {
      console.warn('LLM enhancement failed:', error);
      return rawGraph;
    }
  };
  
  // Format and enhance graph data
  useEffect(() => {
    const processGraph = async () => {
      if (!file?.graph) {
        setStyledGraph(null);
        return;
      }
      
      setIsEnhancing(true);
      
      const formatted = formatGraphData(file.graph);
      console.log("Formatted graph:", formatted);
      
      if (formatted && formatted.nodes && formatted.nodes.length > 0) {
        const enhanced = await enhanceGraphWithLLM(formatted);
        console.log("Enhanced graph:", enhanced);
        setStyledGraph(enhanced);
      } else {
        console.log("No valid formatted graph");
        setStyledGraph(null);
      }
      
      setIsEnhancing(false);
    };
    
    processGraph();
  }, [file?.graph]);
  
  const localGraph = styledGraph;
  
  console.log("GraphStage - raw graph:", file?.graph);
  console.log("GraphStage - formatted graph:", localGraph);
  console.log("GraphStage - nodeIds:", localGraph?.nodes?.map(n => n.id));
  console.log("GraphStage - edge sources/targets:", localGraph?.links?.map(l => ({source: l.source, target: l.target})));

  useEffect(() => {
    if (graphRef.current && localGraph?.nodes?.length > 0) {
      graphRef.current.zoomToFit(500);
    }
  }, [localGraph]);

  const handleNodeClick = (node) => {
    setSelectedNode(node);
  };

  // Add effect to stabilize after initial load
  useEffect(() => {
    if (graphRef.current && localGraph?.nodes?.length > 0) {
      setTimeout(() => {
        // Stop the simulation after it settles
        graphRef.current.d3Force('charge').strength(-30);
        graphRef.current.d3Force('link').strength(0.5);
      }, 3000);
    }
  }, [localGraph]);

  const getConnectedNodes = (nodeId) => {
    if (!localGraph) return [];
    
    console.log("Looking for connections for node:", nodeId);
    console.log("Available links:", localGraph.links.slice(0, 3));
    
    const connections = localGraph.links
      .filter(link => {
        // Handle both string IDs and object references
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        const isConnected = sourceId === nodeId || targetId === nodeId;
        
        if (isConnected) {
          console.log("Found connection:", {sourceId, targetId, nodeId});
        }
        
        return isConnected;
      })
      .map(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
        const connectedId = sourceId === nodeId ? targetId : sourceId;
        return localGraph.nodes.find(n => n.id === connectedId);
      })
      .filter(Boolean);
      
    console.log("Connected nodes found:", connections.length);
    return connections;
  };

  return (
    <div style={{ 
      width: "100%", 
      height: "100vh", 
      position: "relative",
      backgroundColor: "#111"
    }}>
      {/* Header */}
      <div style={{ 
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        padding: "1rem",
        zIndex: 10,
        backgroundColor: "rgba(0,0,0,0.8)",
        color: "#fff"
      }}>
        <h2 style={{ 
          margin: 0,
          fontSize: "1.25rem", 
          color: "#00ffff" 
        }}>
          Insights Graph
        </h2>
        
        {file && (
          <div style={{ color: "#666", fontSize: "0.8rem", marginTop: "0.5rem" }}>
            {file.name} • {localGraph?.nodes?.length || 0} nodes • {localGraph?.links?.length || 0} connections
            <button 
              onClick={() => graphRef.current?.zoomToFit(1000)}
              style={{
                marginLeft: "1rem",
                padding: "0.25rem 0.5rem",
                fontSize: "0.7rem",
                background: "#333",
                color: "#00ffff",
                border: "1px solid #555",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              Fit to View
            </button>
          </div>
        )}
      </div>

      {/* Graph area */}
      <div style={{ 
        position: "absolute",
        top: "80px",
        left: 0,
        right: 0,
        bottom: 0
      }}>
        {localGraph && localGraph.nodes?.length > 0 ? (
          <ForceGraph2D
            ref={graphRef}
            graphData={localGraph}
            nodeLabel="text"
            nodeAutoColorBy="speaker"
            linkDirectionalParticles={2}       // Fewer particles for cleaner look
            linkDirectionalArrowLength={4}     
            linkCurvature={0.1}                // Less curve for cleaner lines
            enableNodeDrag={true}
            enablePanInteraction={true}        
            enableZoomInteraction={true}       
            backgroundColor="#000000"
            linkColor={() => '#00ffff'}        
            linkWidth={1}                      // Thinner links 
            linkOpacity={0.6}                  
            // Physics settings for stability
            d3AlphaDecay={0.02}               // Slower cooling
            d3AlphaMin={0.001}                // Don't stop completely
            d3VelocityDecay={0.3}             // More dampening
            linkDistance={80}                 // Consistent link distance
            linkStrength={1}                  // Strong links
            nodeVal={node => {
              const connections = localGraph.links.filter(link => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return sourceId === node.id || targetId === node.id;
              }).length;
              return Math.max(8, connections * 3); // Bigger nodes
            }}
            onNodeClick={handleNodeClick}
          />
        ) : (
          <div style={{ 
            color: "#666", 
            padding: "2rem",
            textAlign: "center",
            paddingTop: "2rem"
          }}>
            {!file && "No file selected"}
            {file && !file.graph && "File has no graph data"}
            {file && file.graph && (!localGraph?.nodes || localGraph.nodes.length === 0) && "Graph data is invalid or empty"}
          </div>
        )}
      </div>
      
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
            <div className="main-text">
              {selectedNode.text}
            </div>
            
            <div className="node-meta">
              <span className="speaker">{selectedNode.speaker}</span>
              <span className="sentiment">{selectedNode.sentiment}</span>
            </div>
            
            <div className="connections">
              <h4>Connected to ({getConnectedNodes(selectedNode.id).length})</h4>
              {getConnectedNodes(selectedNode.id).map(node => (
                <div key={node.id} className="connected-item">
                  {node.text?.substring(0, 60)}...
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}