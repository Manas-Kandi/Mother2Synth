from dotenv import load_dotenv
import os
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Load from .env

gemini_model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
from datetime import datetime
import re
import time
from uuid import uuid4

UPLOAD_DIR = "uploads"
CLEANED_DIR = "cleaned"
ATOMS_DIR = "atoms"
ANNOTATED_DIR = "annotated"
GRAPH_DIR = "graph"

LLM_PROMPT = """
You are a senior UX research assistant.

You will be given raw transcript text extracted from a PDF. This text may include:
- Page numbers, headers/footers, and other formatting artifacts
- Broken sentences or poor line breaks
- Missing or inconsistent speaker labels
- Boilerplate content unrelated to the conversation

Your task is to return a cleaned and structured transcript that is ready for downstream synthesis.

Instructions:
1. Remove noise such as page numbers, headers/footers, and irrelevant boilerplate.
2. Repair formatting issues like broken lines or mid-sentence splits.
3. Preserve speaker turns clearly. If speaker labels are inconsistent or missing:
   - **Use conversational context to separate distinct speakers.**
   - **Assign clearly differentiated pseudonyms**, like "Speaker 1", "Speaker 2", etc.
   - If a real name is obvious (e.g. mentioned multiple times as self-introduction), use it instead.
4. If a speaker is guessed, annotate with `[inferred]`.
5. If part of the text is unreadable, mark it as `[unintelligible]`.
6. **Do not hallucinate content** — your job is to clean and segment, not create new ideas.

Format:
- Output as plain text
- Each paragraph should start with a speaker label, like:

ERIC: I grew up in Pittsburgh. I loved fishing with my dad.
AJENA [inferred]: That sounds peaceful. My family used to hike a lot.

Here is the raw transcript:
---
{raw_text}
---
Return only the cleaned, speaker-separated transcript.
"""

def run_llm_normalizer(raw_text: str) -> str:
    # If text is extremely long, truncate with warning
    if len(raw_text) > 50000:
        print(f"\u26A0\uFE0F Text very long ({len(raw_text)} chars), truncating to 50k")
        raw_text = raw_text[:50000] + "\n\n[... text truncated due to length ...]"
    prompt = LLM_PROMPT.replace("{raw_text}", raw_text)
    for attempt in range(2):
        try:
            print(f"\U0001F9E0 Normalizing attempt {attempt + 1}")
            response = gemini_model.generate_content(prompt)
            result = response.text.strip()
            if result and len(result) > 10:  # Basic sanity check
                print(f"\u2705 Normalization successful ({len(result)} chars)")
                return result
            else:
                raise ValueError("Normalizer returned empty or very short result")
        except Exception as e:
            print(f"\u274C Normalization error (attempt {attempt + 1}): {e}")
            if attempt < 1:  # Try once more
                time.sleep(1)
                continue
    print("\U0001F6AB Normalization failed, returning raw text")
    return f"[Normalization failed - returning raw text]\n\n{raw_text}"

ATOMISER_PROMPT = """You are an “Atomic Evidence Splitter”.\n\nInput: cleaned transcript  \nOutput: JSON list of atoms.\n\nSchema per atom:\n{\n  \"id\": \"<uuid>\",\n  \"speaker\": \"<speaker>\",\n  \"text\": \"<1–3 sentence idea>\",\n  \"context\": \"<±2 sentences for context>\",\n  \"entities\": {\n    \"objects\": [],\n    \"tasks\": [],\n    \"emotions\": []\n  },\n  \"confidence\": \"high|medium|low\"\n}\n\nRules:\n- Cut only at natural idea boundaries.  \n- Never merge speakers.  \n- Entities must appear verbatim in text.  \n- If unsure, mark confidence=low and shorten text.  \n\nReturn ONLY valid JSON. No commentary.\n\nTranscript:\n{transcript}\n"""

def fix_json_syntax(raw_json: str) -> str:
    """Try to fix common JSON syntax issues"""
    # Remove trailing commas before closing brackets
    raw_json = re.sub(r',([\s]*[}\]])', r'\1', raw_json)
    # (Optional) Add more fixes as needed
    return raw_json

def chunk_and_atomise(clean_text: str, source_file: str, chunk_size: int = 8000) -> list[dict]:
    """Split long text into chunks and atomise each separately"""
    lines = clean_text.split('\n')
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk + line) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    print(f"\U0001F4E6 Split into {len(chunks)} chunks")
    all_atoms = []
    for i, chunk in enumerate(chunks):
        print(f"\U0001F501 Processing chunk {i + 1}/{len(chunks)}")
        chunk_atoms = run_llm_atomiser_single(chunk, source_file, i + 1)
        all_atoms.extend(chunk_atoms)
        time.sleep(0.5)  # Brief pause between chunks
    return all_atoms

def run_llm_atomiser_single(chunk_text: str, source_file: str, chunk_num: int) -> list[dict]:
    """Atomise a single chunk - simplified version without recursion"""
    prompt = ATOMISER_PROMPT.replace("{transcript}", chunk_text)
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
        # Clean up
        raw = re.sub(r'^```(?:json)?', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
        raw = fix_json_syntax(raw)
        atoms = json.loads(raw)
        if isinstance(atoms, list):
            for atom in atoms:
                atom.setdefault("id", str(uuid4()))
                atom["source_file"] = f"{source_file} (chunk {chunk_num})"
            return atoms
    except Exception as e:
        print(f"Chunk {chunk_num} failed: {e}")
    # Return empty list for failed chunks
    return []

def run_llm_atomiser(clean_text: str, source_file: str) -> list[dict]:
    # If text is too long, chunk it
    if len(clean_text) > 15000:  # Adjust threshold as needed
        print(f"\U0001F4CF Text too long ({len(clean_text)} chars), chunking...")
        return chunk_and_atomise(clean_text, source_file)
    prompt = ATOMISER_PROMPT.replace("{transcript}", clean_text)
    # Try multiple times with different strategies
    for attempt in range(3):
        try:
            response = gemini_model.generate_content(prompt)
            raw = response.text.strip()
            print(f"\U0001F9E0 GEMINI RAW (Atomiser, attempt {attempt + 1}):")
            print(repr(raw[:500]) + "..." if len(raw) > 500 else repr(raw))
            # Clean up markdown fences more aggressively
            raw = re.sub(r'^```(?:json)?', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'```$', '', raw, flags=re.MULTILINE)
            raw = raw.strip()
            # Try to fix common JSON issues
            raw = fix_json_syntax(raw)
            atoms = json.loads(raw)
            # Validate and enrich atoms
            if not isinstance(atoms, list):
                raise ValueError("Expected list of atoms")
            valid_atoms = []
            for atom in atoms:
                if isinstance(atom, dict) and "text" in atom:
                    atom.setdefault("id", str(uuid4()))
                    atom["source_file"] = source_file
                    valid_atoms.append(atom)
            if valid_atoms:
                print(f"\u2705 Successfully parsed {len(valid_atoms)} atoms")
                return valid_atoms
            else:
                raise ValueError("No valid atoms found")
        except json.JSONDecodeError as e:
            print(f"\u274C JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < 2:  # Try again with more aggressive prompt
                prompt = ATOMISER_PROMPT.replace("{transcript}", clean_text[:10000])  # Truncate
                continue
        except Exception as e:
            print(f"\u274C Other error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(1)  # Brief pause before retry
                continue
    # All attempts failed, return error atom
    print("\U0001F6AB All atomisation attempts failed, returning error atom")
    return [{
        "id": str(uuid4()),
        "speaker": "ERROR",
        "text": f"[Atomiser failed after 3 attempts. Text length: {len(clean_text)} chars. Last error: JSON parsing failed]",
        "context": "",
        "entities": {"objects": [], "tasks": [], "emotions": []},
        "confidence": "low",
        "source_file": source_file
    }]

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    return full_text

# 🔁 Reset uploads/ folder on server start
#if os.path.exists(UPLOAD_DIR):
#    shutil.rmtree(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(ATOMS_DIR, exist_ok=True)
os.makedirs(ANNOTATED_DIR, exist_ok=True)
os.makedirs(GRAPH_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_credentials=True,
)

@app.post("/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    saved_files = []

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_files.append(file.filename)

    print("Saved files:", saved_files)
    return {"message": f"Saved {len(saved_files)} file(s)", "files": saved_files}

@app.get("/normalize")
async def normalize_files():
    upload_dir = "uploads"
    normalized_output = {}

    for filename in os.listdir(upload_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        cleaned_path = os.path.join(CLEANED_DIR, filename.replace(".pdf", ".txt"))

        # 1️⃣  Return cached if it exists
        if os.path.exists(cleaned_path):
            with open(cleaned_path, "r", encoding="utf-8") as f:
                cleaned_text = f.read()
        else:
            # 2️⃣  Run LLM once, then cache
            pdf_path = os.path.join(upload_dir, filename)
            raw_text = extract_text_from_pdf(pdf_path)
            cleaned_text = run_llm_normalizer(raw_text)
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(cleaned_text)

        normalized_output[filename] = cleaned_text

    return normalized_output


@app.get("/normalize/{filename}")
async def normalize_file(filename: str):
    cleaned_path = os.path.join(CLEANED_DIR, filename.replace(".pdf", ".txt"))
    if os.path.exists(cleaned_path):
        with open(cleaned_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    pdf_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="File not found")
    raw_text = extract_text_from_pdf(pdf_path)
    cleaned_text = run_llm_normalizer(raw_text)
    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    return {"content": cleaned_text}

@app.get("/atomise")
async def atomise_files():
    upload_dir = "uploads"
    atomised_output = {}

    for filename in os.listdir(upload_dir):
        if not filename.lower().endswith(".pdf"):
            continue

        atoms_path = os.path.join(ATOMS_DIR, filename.replace(".pdf", ".json"))

        # 1️⃣  Return cached if it exists
        if os.path.exists(atoms_path):
            with open(atoms_path, "r", encoding="utf-8") as f:
                atoms = json.load(f)
        else:
            # 2️⃣  Run LLM once, then cache
            pdf_path = os.path.join(upload_dir, filename)
            full_text = extract_text_from_pdf(pdf_path)
            clean_text = run_llm_normalizer(full_text)  # uses cached cleaned.txt if already there
            atoms = run_llm_atomiser(clean_text, filename)

            with open(atoms_path, "w", encoding="utf-8") as f:
                json.dump(atoms, f, indent=2, ensure_ascii=False)

        atomised_output[filename] = atoms

    return atomised_output


ANNOTATOR_PROMPT = """You are a UX-insight extractor.\n\nReturn JSON:\n\n{\n  \"insights\": [\n    {\"type\": \"<meta-category>\", \"label\": \"<≤3 words>\", \"weight\": 0.0-1.0}\n  ],\n  \"tags\": [\"keyword1\", \"keyword2\"]\n}\n\nAllowed types & examples\npersona: mobile user | admin | new hire  \npain: login friction | hidden cost | broken flow  \nemotion: annoyance | anxiety | delight  \nroot_cause: validation bug | slow backend  \nimpact: task abandon | time lost  \ncontext: on-the-go | multitasking  \ndevice: Android | iPhone | desktop  \nchannel: web | app | phone call  \nfrequency: daily | weekly | first-time  \nseverity: blocker | minor | workaround exists\n\nRules\n- Emit 0-2 insights per type, ≤8 total  \n- weight = confidence 0-1  \n- labels verbatim when possible  \n- skip any you can’t ground\n\nQuote:\n{atom_text}\n"""

def annotate_atom(text: str) -> dict:
    prompt = ANNOTATOR_PROMPT.replace("{atom_text}", text)
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r'^```(?:json)?|```$', '', raw, flags=re.M).strip()
        payload = json.loads(raw)
        return {
            "insights": payload.get("insights", []),
            "tags":     payload.get("tags", [])
        }
    except Exception as e:
        print("annotate_atom error:", e)
        return {"insights": [], "tags": []}

@app.post("/annotate")
async def annotate_atoms(atoms: list[dict], filename: str):
    """
    Expects query param ?filename=somefile.pdf
    """
    annotated_path = os.path.join(
        ANNOTATED_DIR,
        filename.replace(".pdf", ".json")
    )

    # 1️⃣  Return cached if it exists
    if os.path.exists(annotated_path):
        with open(annotated_path, "r", encoding="utf-8") as f:
            enriched = json.load(f)
    else:
        # 2️⃣  Run LLM once, then cache
        enriched = []
        for atom in atoms:
            tags = annotate_atom(atom["text"])
            enriched.append({**atom, **tags})

        with open(annotated_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)

    return enriched

def clean_transcript(raw_text: str) -> str:
    lines = raw_text.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()
        if (
            not line
            or "page" in line.lower()
            or "confidential" in line.lower()
            or line.isupper()
        ):
            continue
        cleaned.append(line)

    return "\n".join(cleaned)

GRAPH_BUILDER_PROMPT = """You are an insight-web v2 architect.\n\nInput: list of annotated atoms (with insights array).\n\nGoals\n1. Exact edges: keep "shared label" edges (weight = min weight ≥ 0.7).\n2. Inference edges: create "inferred_<type>" edge when two atoms have semantically related insights (e.g., "login friction" ≈ "wrong password\"); weight = average of the two insight weights, threshold ≥ 0.75.\n3. Auto-themes: group atoms into named themes (≤ 3 words) if ≥ 3 atoms share dominant insight patterns.\n4. Auto-journey: create lightweight "as-is" journey by ordering atoms chronologically and tagging each step with dominant pain + emotion.\n\nOutput JSON:\n{\n  "nodes": [...],\n  "edges": [...],\n  "clusters": {...},\n  "themes": [\n    {\"name\": \"login friction\", \"atoms\": [...], \"dominant_insights\": {\"pain\": \"login friction\", \"emotion\": \"frustration\"}, \"pain_score\": 0.95}\n  ],\n  "journey": [\n    {\"step\": \"login attempt\", \"pain\": \"wrong password\", \"emotion\": \"frustration\", \"atoms\": [...]}\n  ],\n  "facets": [...]\n}\n\nRules\n- Exact edge: same label, both weights ≥ 0.7.  \n- Inference edge: semantic similarity ≥ 0.75.  \n- Theme: ≥ 3 atoms.  \n- Journey: keep chronological order.  \n\nReturn strict JSON only."""

@app.post("/graph")
async def build_graph(atoms: list[dict], filename: str):
    graph_path = os.path.join(GRAPH_DIR, filename.replace(".pdf", ".json"))
    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Build nodes
    nodes = atoms
    # Build edges based on shared insights
    edges = []
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            node1 = nodes[i]
            node2 = nodes[j]
            shared = find_shared_insights(node1, node2)
            if shared:
                # Use the first shared insight for label/weight
                label, _ = shared[0]
                edges.append({
                    "source": node1["id"],
                    "target": node2["id"],
                    "label": label,
                    "weight": 1  # or use a more meaningful value if desired
                })

    graph = {
        "nodes": nodes,
        "edges": edges,
        "clusters": {},
        "facets": [],
        "themes": [],
        "nodes_desc": "List of every atom.",
        "edges_desc": "Links between atoms sharing high-weight insights.",
        "clusters_desc": "Auto-groups per insight label (≥ 2 atoms)."
    }

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
    return graph

def find_shared_insights(node1, node2):
    set1 = {(i["type"], i["label"]) for i in node1.get("insights", [])}
    set2 = {(i["type"], i["label"]) for i in node2.get("insights", [])}
    return list(set1 & set2)  # intersection

@app.get("/projects")
async def list_projects():
    """
    Returns a map:
    {
      "demo.pdf": {
        "cleaned": true,
        "atoms": true,
        "annotated": true,
        "graph": true
      },
      ...
    }
    """
    projects = {}
    for filename in os.listdir("uploads"):
        if not filename.lower().endswith(".pdf"):
            continue

        base = filename.replace(".pdf", "")
        projects[filename] = {
            "cleaned": os.path.exists(os.path.join(CLEANED_DIR, f"{base}.txt")),
            "atoms": os.path.exists(os.path.join(ATOMS_DIR, f"{base}.json")),
            "annotated": os.path.exists(os.path.join(ANNOTATED_DIR, f"{base}.json")),
            "graph": os.path.exists(os.path.join(GRAPH_DIR, f"{base}.json")),
        }
    return projects

@app.get("/cached/{stage}/{filename}")
async def get_cached(stage: str, filename: str):
    """
    stage = cleaned | atoms | annotated | graph
    filename = demo.pdf
    Returns the cached JSON (or plain text for cleaned)
    """
    base = filename.replace(".pdf", "")
    paths = {
        "cleaned":   os.path.join(CLEANED_DIR,   f"{base}.txt"),
        "atoms":     os.path.join(ATOMS_DIR,     f"{base}.json"),
        "annotated": os.path.join(ANNOTATED_DIR, f"{base}.json"),
        "graph":     os.path.join(GRAPH_DIR,     f"{base}.json"),
    }
    path = paths.get(stage)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not cached")

    if stage == "cleaned":
        return PlainTextResponse(open(path, encoding="utf-8").read())
    else:
        return JSONResponse(json.load(open(path, encoding="utf-8")))

@app.delete("/projects/{filename}")
async def delete_project(filename: str):
    """
    filename = demo.pdf
    Removes:
      uploads/demo.pdf
      cleaned/demo.txt
      atoms/demo.json
      annotated/demo.json
      graph/demo.json
    """
    base = filename.replace(".pdf", "")
    files_to_delete = [
        os.path.join("uploads", filename),
        os.path.join(CLEANED_DIR, f"{base}.txt"),
        os.path.join(ATOMS_DIR, f"{base}.json"),
        os.path.join(ANNOTATED_DIR, f"{base}.json"),
        os.path.join(GRAPH_DIR, f"{base}.json"),
    ]
    for path in files_to_delete:
        if os.path.exists(path):
            os.remove(path)

    return {"ok": True}

# --- Theme Clustering Prompt and Endpoint ---
THEME_CLUSTER_PROMPT = '''You are a UX research theme clustering assistant.\n\nInput: a list of annotated atoms, each with speaker, text, insights, and tags.\n\nYour task:\n- Cluster the atoms into 3-8 high-level themes.\n- Each theme should have:\n  - a short, descriptive name (≤4 words)\n  - a 1-2 sentence summary\n  - a list of atom IDs belonging to the theme\n- Do not create overlapping themes.\n- Every atom must belong to exactly one theme.\n- Use only the information in the atoms and their annotations.\n\nReturn strict JSON:\n[\n  {\n    "name": "Theme name",\n    "summary": "Short summary of the theme.",\n    "atom_ids": ["uuid1", "uuid2", ...]\n  },\n  ...\n]\n\nHere are the annotated atoms:\n{atoms}\n'''

@app.post("/themes/initial")
async def generate_initial_themes(atoms: list[dict]):
    prompt = THEME_CLUSTER_PROMPT.replace("{atoms}", json.dumps(atoms, ensure_ascii=False))
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()

        # Debug output
        print("🧠 GEMINI RAW RESPONSE (Themer V1):")
        print(repr(raw))

        # Clean all ```json ... ``` wrappers no matter how they're placed
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        themes = json.loads(raw)
        return themes
    except Exception as e:
        print("Theme clustering error:", e)
        return []

# --- Comments System Data Models ---
class Comment(BaseModel):
    id: int
    text: str
    selectedText: str
    timestamp: str
    position: float
    exchangeIndex: int
    author: str
    filename: str

class CommentRequest(BaseModel):
    exchangeId: int
    comment: Comment

class CommentResponse(BaseModel):
    success: bool
    message: Optional[str] = None

# --- Comments System Helpers ---
COMMENTS_DIR = "data/comments"
os.makedirs(COMMENTS_DIR, exist_ok=True)

def get_comments_file(filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return os.path.join(COMMENTS_DIR, f"{safe_filename}.json")

def load_comments(filename: str) -> Dict:
    comments_file = get_comments_file(filename)
    if os.path.exists(comments_file):
        with open(comments_file, 'r') as f:
            return json.load(f)
    return {"comments": {}, "metadata": {"filename": filename, "created": datetime.now().isoformat()}}

def save_comments(filename: str, comments_data: Dict):
    comments_file = get_comments_file(filename)
    comments_data["metadata"]["updated"] = datetime.now().isoformat()
    with open(comments_file, 'w') as f:
        json.dump(comments_data, f, indent=2)

# --- Comments System Endpoints ---
@app.get("/comments/{filename}")
async def get_comments(filename: str):
    try:
        comments_data = load_comments(filename)
        return comments_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load comments: {str(e)}")

@app.post("/comments/{filename}")
async def add_comment(filename: str, request: CommentRequest) -> CommentResponse:
    try:
        comments_data = load_comments(filename)
        exchange_id = str(request.exchangeId)
        if exchange_id not in comments_data["comments"]:
            comments_data["comments"][exchange_id] = []
        comment_dict = request.comment.dict()
        comment_dict["created"] = datetime.now().isoformat()
        comments_data["comments"][exchange_id].append(comment_dict)
        save_comments(filename, comments_data)
        return CommentResponse(success=True, message="Comment added successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save comment: {str(e)}")

@app.delete("/comments/{filename}/{comment_id}")
async def delete_comment(filename: str, comment_id: int) -> CommentResponse:
    try:
        comments_data = load_comments(filename)
        found = False
        for exchange_id, comments_list in comments_data["comments"].items():
            original_length = len(comments_list)
            comments_data["comments"][exchange_id] = [
                c for c in comments_list if c["id"] != comment_id
            ]
            if len(comments_data["comments"][exchange_id]) != original_length:
                found = True
        if not found:
            raise HTTPException(status_code=404, detail="Comment not found")
        comments_data["comments"] = {k: v for k, v in comments_data["comments"].items() if v}
        save_comments(filename, comments_data)
        return CommentResponse(success=True, message="Comment deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete comment: {str(e)}")

@app.get("/comments/{filename}/export")
async def export_comments(filename: str):
    try:
        comments_data = load_comments(filename)
        synthesis_format = {
            "filename": filename,
            "total_comments": sum(len(comments) for comments in comments_data["comments"].values()),
            "insights": [],
            "quotes": []
        }
        for exchange_id, comments_list in comments_data["comments"].items():
            for comment in comments_list:
                synthesis_format["insights"].append({
                    "exchange_id": int(exchange_id),
                    "text": comment["text"],
                    "author": comment["author"],
                    "timestamp": comment["timestamp"],
                    "quoted_text": comment["selectedText"]
                })
                synthesis_format["quotes"].append({
                    "text": comment["selectedText"],
                    "context": f"Exchange {exchange_id}",
                    "insight": comment["text"],
                    "author": comment["author"]
                })
        return synthesis_format
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export comments: {str(e)}")

@app.get("/synthesis/{filename}/comments")
async def get_synthesis_comments(filename: str):
    return await export_comments(filename)

@app.post("/enhance-graph")
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
        # Remove markdown code fences if present
        if raw.startswith("```json"):
            raw = raw[len("```json"):].strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        styled_nodes = json.loads(raw)
        return styled_nodes
    except Exception as e:
        print("enhance_graph error:", e)
        return []
