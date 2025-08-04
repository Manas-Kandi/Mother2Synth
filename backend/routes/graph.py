import os
import json
from typing import List

from fastapi import APIRouter

from llm import gemini_model
from paths import GRAPH_DIR

router = APIRouter()

GRAPH_BUILDER_PROMPT = """You are an insight-web v2 architect.\n\nInput: list of annotated atoms (with insights array).\n\nGoals\n1. Exact edges: keep \"shared label\" edges (weight = min weight ≥ 0.7).\n2. Inference edges: create \"inferred_<type>\" edge when two atoms have semantically related insights (e.g., \"login friction\" ≈ \"wrong password\"); weight = average of the two insight weights, threshold ≥ 0.75.\n3. Auto-themes: group atoms into named themes (≤ 3 words) if ≥ 3 atoms share dominant insight patterns.\n4. Auto-journey: create lightweight \"as-is\" journey by ordering atoms chronologically and tagging each step with dominant pain + emotion.\n\nOutput JSON:\n{\n  \"nodes\": [...],\n  \"edges\": [...],\n  \"clusters\": {...},\n  \"themes\": [\n    {\"name\": \"login friction\", \"atoms\": [...], \"dominant_insights\": {\"pain\": \"login friction\", \"emotion\": \"frustration\"}, \"pain_score\": 0.95}\n  ],\n  \"journey\": [\n    {\"step\": \"login attempt\", \"pain\": \"wrong password\", \"emotion\": \"frustration\", \"atoms\": [...]}\n  ],\n  \"facets\": [...]\n}\n\nRules\n- Exact edge: same label, both weights ≥ 0.7.  \n- Inference edge: semantic similarity ≥ 0.75.  \n- Theme: ≥ 3 atoms.  \n- Journey: keep chronological order.  \n\nReturn strict JSON only."""


def find_shared_insights(node1: dict, node2: dict) -> List[tuple]:
    """Return intersection of (type, label) insight pairs between two nodes."""
    set1 = {(i["type"], i["label"]) for i in node1.get("insights", [])}
    set2 = {(i["type"], i["label"]) for i in node2.get("insights", [])}
    return list(set1 & set2)


@router.post("/graph")
async def build_graph(atoms: List[dict], filename: str, project_slug: str = None):
    from dropzone import dropzone_manager
    if not project_slug:
        raise HTTPException(status_code=400, detail="project_slug query param required")
    graph_path = dropzone_manager.get_project_path(project_slug, "graphs") / filename.replace(".pdf", ".json")
    print(f"[DropZone] Graph: graph_path={graph_path}")
    if graph_path.exists():
        with open(graph_path, "r", encoding="utf-8") as f:
            return json.load(f)

    nodes = atoms
    edges = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            shared = find_shared_insights(nodes[i], nodes[j])
            if shared:
                label, _ = shared[0]
                edges.append({
                    "source": nodes[i]["id"],
                    "target": nodes[j]["id"],
                    "label": label,
                    "weight": 1,
                })

    graph = {
        "nodes": nodes,
        "edges": edges,
        "clusters": {},
        "facets": [],
        "themes": [],
        "nodes_desc": "List of every atom.",
        "edges_desc": "Links between atoms sharing high-weight insights.",
        "clusters_desc": "Auto-groups per insight label (≥ 2 atoms).",
    }

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    return graph


THEME_CLUSTER_PROMPT = '''You are a UX research theme clustering assistant.\n\nInput: a list of annotated atoms, each with speaker, text, insights, and tags.\n\nYour task:\n- Cluster the atoms into 3-8 high-level themes.\n- Each theme should have:\n  - a short, descriptive name (≤4 words)\n  - a 1-2 sentence summary\n  - a list of atom IDs belonging to the theme\n- Do not create overlapping themes.\n- Every atom must belong to exactly one theme.\n- Use only the information in the atoms and their annotations.\n\nReturn strict JSON:\n[\n  {\n    "name": "Theme name",\n    "summary": "Short summary of the theme.",\n    "atom_ids": ["uuid1", "uuid2", ...]\n  },\n  ...\n]\n\nHere are the annotated atoms:\n{atoms}\n'''


@router.post("/themes/initial")
async def generate_initial_themes(atoms: List[dict]):
    prompt = THEME_CLUSTER_PROMPT.replace("{atoms}", json.dumps(atoms, ensure_ascii=False))
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
        print("🧠 GEMINI RAW RESPONSE (Themer V1):")
        print(repr(raw))
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        themes = json.loads(raw)
        return themes
    except Exception as e:
        print("Theme clustering error:", e)
        return []


@router.post("/enhance-graph")
async def enhance_graph(request: dict):
    nodes = request.get("nodes", [])
    if not nodes:
        return []
    prompt = '''\
Analyze these user research insights and assign each one:
1. A color (hex code) - red for pain points, green for positive behaviors, blue for technical issues, orange for comparisons, purple for emotions
2. An emoji icon that represents the content
3. A short 1-2 word label that captures the essence
4. A category (pain, behavior, technical, comparison, emotion, other)

Return JSON array with: [{"id": "...", "color": "#ff4757", "icon": "😤", "label": "frustration", "category": "pain"}]

Insights: {insights}
'''.replace("{insights}", json.dumps(nodes, ensure_ascii=False))
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        styled_nodes = json.loads(raw)
        return styled_nodes
    except Exception as e:
        print("enhance_graph error:", e)
        return []
