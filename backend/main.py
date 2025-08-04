from app import app
import os
import json
import re
import time
from fastapi import Request, HTTPException
from quality_guard import run_quality_guard
from chat_assistant import ChatAssistant

# Add this near the top with other directory constants
GRAPHS_DIR = "graphs"
os.makedirs(GRAPHS_DIR, exist_ok=True)

# Fix the GRAPH_BUILDER_PROMPT to use the correct placeholder
GRAPH_BUILDER_PROMPT = """You are an insight-web v2 architect.\n\nInput: list of annotated atoms (with insights array).\n\nGoals\n1. Exact edges: keep \"shared label\" edges (weight = min weight \u2265 0.7).\n2. Inference edges: create \"inferred_<type>\" edge when two atoms have semantically related insights (e.g., \"login friction\" \u2248 \"wrong password\"); weight = average of the two insight weights, threshold \u2265 0.75.\n3. Auto-themes: group atoms into named themes (\u2264 3 words) if \u2265 3 atoms share dominant insight patterns.\n4. Auto-journey: create lightweight \"as-is\" journey by ordering atoms chronologically and tagging each step with dominant pain + emotion.\n\nOutput JSON:\n{\n  \"nodes\": [...],\n  \"edges\": [...],\n  \"clusters\": {...},\n  \"themes\": [\n    {\"name\": \"login friction\", \"atoms\": [...], \"dominant_insights\": {\"pain\": \"login friction\", \"emotion\": \"frustration\"}, \"pain_score\": 0.95}\n  ],\n  \"journey\": [\n    {\"step\": \"login attempt\", \"pain\": \"wrong password\", \"emotion\": \"frustration\", \"atoms\": [...]}\n  ],\n  \"facets\": [...]\n}\n\nRules\n- Exact edge: same label, both weights \u2265 0.7.  \n- Inference edge: semantic similarity \u2265 0.75.  \n- Theme: \u2265 3 atoms.  \n- Journey: keep chronological order.  \n\nReturn strict JSON only.\n\nAnnotated atoms:\n{atoms_json}"""

@app.post("/graph-build")
async def build_graph(request: Request):
    """
    Build research graph from annotated atoms
    Expected query param: ?filename=somefile.pdf
    """
    filename = request.query_params.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="filename query param required")
    
    # Check if we have annotated atoms for this file
    annotated_path = os.path.join(ANNOTATED_DIR, filename.replace(".pdf", ".json"))
    if not os.path.exists(annotated_path):
        raise HTTPException(status_code=404, detail=f"No annotated data found for {filename}")
    
    # Load annotated atoms
    with open(annotated_path, "r", encoding="utf-8") as f:
        annotated_atoms = json.load(f)
    
    if not annotated_atoms:
        return {"nodes": [], "edges": [], "clusters": {}, "themes": [], "journey": [], "facets": []}
    
    # Check cache first
    graph_path = os.path.join(GRAPHS_DIR, filename.replace(".pdf", ".json"))
    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Build graph using LLM
    print(f"\U0001F517 Building graph for {filename} with {len(annotated_atoms)} atoms")
    graph_data = run_llm_graph_builder(annotated_atoms, filename)
    
    # Cache the result
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
    
    return graph_data


# Quality Guard endpoint
@app.post("/quality-guard")
async def run_quality_validation(request: Request):
    """Run comprehensive quality validation"""
    filename = request.query_params.get("filename")
    project_slug = request.query_params.get("project_slug")

    if not filename or not project_slug:
        raise HTTPException(status_code=400, detail="filename and project_slug query params required")
    
    # Load required data
    themes_path = f"/DropZone/{project_slug}/graphs/{filename.replace('.pdf', '_themes.json')}"
    atoms_path = f"/DropZone/{project_slug}/atoms/{filename.replace('.pdf', '_atoms.json')}"
    insights_path = f"/DropZone/{project_slug}/graphs/{filename.replace('.pdf', '_insights.json')}"
    board_path = f"/DropZone/{project_slug}/boards/{filename.replace('.pdf', '_board.json')}"

    try:
        print(f"Reading themes file: {themes_path}")
        with open(themes_path, 'r') as f:
            themes = json.load(f)
        print(f"Reading atoms file: {atoms_path}")
        with open(atoms_path, 'r') as f:
            atoms = json.load(f)
        print(f"Reading insights file: {insights_path}")
        with open(insights_path, 'r') as f:
            insights = json.load(f)
        print(f"Reading board file: {board_path}")
        with open(board_path, 'r') as f:
            board_data = json.load(f)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Required file not found: {e}")
    
    validation_report = run_quality_guard(project_slug, themes, atoms, insights, board_data)
    return validation_report


# Chat Assistant endpoint
@app.post("/chat")
async def chat_with_assistant(request: Request):
    """Chat with the LLM research assistant"""
    data = await request.json()
    message = data.get('message')
    project_slug = data.get('project')
    context = data.get('context', {})
    
    if not message or not project_slug:
        raise HTTPException(status_code=400, detail="message and project required")
    
    assistant = ChatAssistant(project_slug)
    response = assistant.process_message(message, context)
    
    return response


# Conversation history endpoint
@app.get("/chat/history")
async def get_chat_history(request: Request):
    """Get chat conversation history"""
    project_slug = request.query_params.get("project")
    if not project_slug:
        raise HTTPException(status_code=400, detail="project query param required")
    
    assistant = ChatAssistant(project_slug)
    summary = assistant.get_conversation_summary()
    return summary


def run_llm_graph_builder(annotated_atoms: list[dict], source_file: str) -> dict:
    """Build graph from annotated atoms using LLM"""
    # Prepare input - truncate if too long
    atoms_text = json.dumps(annotated_atoms, indent=1)
    if len(atoms_text) > 15000:
        print(f"\u26A0\uFE0F Atoms data very long ({len(atoms_text)} chars), truncating to 15k")
        atoms_text = atoms_text[:15000] + "\n... [truncated]"
    
    prompt = GRAPH_BUILDER_PROMPT.replace("{atoms_json}", atoms_text)
    
    for attempt in range(2):
        try:
            print(f"\U0001F9E0 Graph building attempt {attempt + 1}")
            response = gemini_model.generate_content(prompt)
            raw = response.text.strip()
            
            # Clean up JSON
            raw = re.sub(r'^```(?:json)?|```$', '', raw, flags=re.M).strip()
            raw = fix_json_syntax(raw)
            
            graph_data = json.loads(raw)
            
            # Validate basic structure
            if not isinstance(graph_data.get("nodes"), list):
                graph_data["nodes"] = []
            if not isinstance(graph_data.get("edges"), list):
                graph_data["edges"] = []
            
            print(f"\u2705 Graph built: {len(graph_data.get('nodes', []))} nodes, {len(graph_data.get('edges', []))} edges")
            return graph_data
            
        except Exception as e:
            print(f"\u274C Graph building error (attempt {attempt + 1}): {e}")
            if attempt < 1:
                time.sleep(1)
                continue
    
    # Fallback: create simple graph from atoms
    print("\U0001F501 Creating fallback graph")
    return create_fallback_graph(annotated_atoms, source_file)


def create_fallback_graph(annotated_atoms: list[dict], source_file: str) -> dict:
    """Create a simple fallback graph when LLM fails"""
    nodes = []
    edges = []
    
    for i, atom in enumerate(annotated_atoms):
        # Create node for each atom
        node = {
            "id": atom.get("id", f"atom_{i}"),
            "text": atom.get("text", "")[:100] + "..." if len(atom.get("text", "")) > 100 else atom.get("text", ""),
            "speaker": atom.get("speaker", "unknown"),
            "insights": atom.get("insights", []),
            "tags": atom.get("tags", [])
        }
        nodes.append(node)
        
        # Simple edge creation based on shared tags
        if i > 0 and atom.get("tags"):
            prev_atom = annotated_atoms[i-1]
            shared_tags = set(atom.get("tags", [])) & set(prev_atom.get("tags", []))
            if shared_tags:
                edges.append({
                    "source": prev_atom.get("id", f"atom_{i-1}"),
                    "target": atom.get("id", f"atom_{i}"),
                    "type": "shared_tag",
                    "label": list(shared_tags)[0],
                    "weight": 0.5
                })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": {},
        "themes": [],
        "journey": [],
        "facets": []
    }
