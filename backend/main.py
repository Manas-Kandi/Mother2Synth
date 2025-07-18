import google.generativeai as genai
genai.configure(api_key="AIzaSyBLv7dA4tI0bZGo6DXGAQA1_-fKRqnieYc")  # ⬅️ Replace this with your real key

gemini_model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import json
import re
import time
from uuid import uuid4
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi import HTTPException

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
    prompt = LLM_PROMPT.replace("{raw_text}", raw_text)
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error from Gemini: {e}")
        return "[LLM error]"

def run_llm_atomiser(clean_text: str) -> list[dict]:
    prompt = (
        "You are an \"Idea Atomiser\" working with cleaned UX research transcripts.\n\n"
        "Your job is to break the transcript into discrete **idea units**, or \"atoms\".\n\n"
        "Each atom must:\n"
        "- Be 1–3 sentences long\n"
        "- Be self-contained (understandable without additional context)\n"
        "- Include only one coherent thought or idea\n"
        "- Include the **speaker label**, preserved as given (e.g., 'AJENA', 'ERIC', or 'SPEAKER 1')\n\n"
        "Guidelines:\n"
        "- Do not combine ideas from different speakers into one atom\n"
        "- If a speaker shifts topics, split that into multiple atoms\n"
        "- Retain any emotional tone or opinion expressed — it may be useful later\n"
        "- Avoid splitting mid-sentence unless absolutely necessary\n\n"
        "Output ONLY a valid JSON list, no extra commentary.\n"
        "Example:\n"
        '[{"speaker": "ERIC", "text": "I grew up in Roanoke and loved spending time outdoors with my brothers."}]\n\n'
        "Here is the cleaned transcript:\n---\n"
        f"{clean_text}\n---"
    )

    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()

        # Remove Markdown fences if present
        import re
        raw = re.sub(r'```(?:json)?|```', '', raw).strip()

        atoms = json.loads(raw)
        if not isinstance(atoms, list):
            raise ValueError("Not a list")
        return atoms
    except Exception as e:
        print("Atomiser failed:", e)
        print("Raw response:", repr(raw))
        return [
            {"speaker": "ERROR", "text": f"[Atomiser failed: {e}]"}
        ]  # non-empty so frontend shows the error

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
            atoms = run_llm_atomiser(clean_text)

            with open(atoms_path, "w", encoding="utf-8") as f:
                json.dump(atoms, f, indent=2, ensure_ascii=False)

        atomised_output[filename] = atoms

    return atomised_output


ANNOTATOR_PROMPT = """
You are a precise tagging assistant.  
Given an idea atom from a UX-research transcript, return ONLY a JSON object with two keys:

- speech_act: pick the single best label from [statement, question, command, complaint, praise, confession, idea, clarification]
- sentiment: pick the single best label from [positive, neutral, negative, mixed]

Atom:
{atom_text}

Return only the JSON object, no extra text.
"""

def annotate_atom(text: str) -> dict:
    prompt = (
        "Tag only. Return JSON: {\"speech_act\":\"...\",\"sentiment\":\"...\"}\n"
        "Allowed speech_act: statement,question,command,complaint,praise,confession,idea,clarification\n"
        "Allowed sentiment: positive,neutral,negative,mixed\n\n"
        f"Text: {text}"
    )
    try:
        response = gemini_model.generate_content(prompt, request_options={"timeout": 5000})  # 5 sec
        raw = response.text.strip()
        print("LLM raw ->", repr(raw))
        m = re.search(r'\{.*?\}', raw, re.DOTALL)
        payload = json.loads(m.group(0))
        return {"speech_act": payload.get("speech_act", "UNKNOWN"),
                "sentiment": payload.get("sentiment", "UNKNOWN")}
    except Exception as e:
        print("annotate_atom error:", e)
        return {"speech_act": "ERROR", "sentiment": "ERROR"}

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

GRAPH_BUILDER_PROMPT = """
You are an **evidence-synthesis architect**.  
You read every atom, then **build a living knowledge graph** that a UX researcher can query, remix, and evolve.

INPUT  
List of annotated atoms (each already contains id, speaker, text, speech_act, sentiment, etc.).

OUTPUT  
A single JSON object with four top-level keys:

1. nodes  
   Same atoms as before, but enriched with **entity arrays** (see below).

2. edges  
   Links between nodes that share **objects, tasks, emotions, personas, or journey steps**.

3. meta  
   High-level **insights** (personas, pain clusters, journey map) distilled from the entire set.

4. facets  
   User-defined, open schema facets (device, channel, cost, etc.) discovered in-text.

----------------------------------------------------
DETAILED SCHEMA
----------------------------------------------------
nodes: [
  {
    "id": "...",
    "speaker": "...",
    "text": "...",
    "speech_act": "...",
    "sentiment": "...",
    "entities": {
      "objects": ["password field", "reset email"],
      "tasks": ["login", "fill form"],
      "emotions": ["frustration"],
      "personas": ["mobile user"],
      "journey_step": "reset attempt"
    }
  }
]

edges: [
  {
    "source": "node_id",
    "target": "node_id",
    "type": "shared_object|shared_task|shared_emotion|shared_persona|journey_flow",
    "label": "concise label ≤15 chars"
  }
]

meta: {
  "personas": ["frustrated mobile user", "admin"],
  "pain_clusters": ["login friction", "missing autosave"],
  "journey_map": [
    {"step": "login attempt", "sentiment": "negative", "atoms": ["a1","a3"]},
    {"step": "reset attempt", "sentiment": "negative", "atoms": ["a4","a5"]}
  ],
  "top_objects": ["password field", "reset email", "form"],
  "top_tasks": ["login", "reset"]
}

facets: {
  "device": ["desktop", "mobile"],
  "channel": ["app", "website"],
  "cost": ["free", "paid"],
  "frequency": ["daily", "weekly"]
}
----------------------------------------------------
RULES
----------------------------------------------------
1. **Extract entities verbatim**; no paraphrasing.  
2. **Only create edges when commonality is explicit** in text.  
3. **Keep labels concise** (≤15 chars).  
4. **Meta insights must be evidence-backed** (reference atom IDs in `journey_map`).  
5. **Facets are optional**; omit if absent.  
6. **Return strict JSON** with keys: nodes, edges, meta, facets.

EXAMPLE INPUT  
[{"id":"a1","speaker":"Speaker 1","text":"I wait for the reset email","sentiment":"negative"}]

EXAMPLE OUTPUT  
{"nodes":[...],"edges":[...],"meta":{...},"facets":{...}}
"""

@app.post("/graph")
async def build_graph(atoms: list[dict], filename: str):
    """
    Expects query param ?filename=somefile.pdf
    """
    graph_path = os.path.join(
        GRAPH_DIR,
        filename.replace(".pdf", ".json")
    )

    # 1️⃣  Return cached if it exists
    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            graph = json.load(f)
    else:
        # 2️⃣  Run LLM once, then cache
        for atom in atoms:
            atom.setdefault("id", str(uuid4()))

        prompt = GRAPH_BUILDER_PROMPT.replace(
            "{atoms}",
            json.dumps(atoms, ensure_ascii=False)
        )
        try:
            response = gemini_model.generate_content(prompt)
            raw = response.text.strip()
            if raw.startswith("```json"):
                raw = raw.split("```", 1)[1].strip()
            graph = json.loads(raw)
        except Exception as e:
            print("Graph builder error:", e)
            graph = {"nodes": atoms, "edges": [], "meta": {}, "facets": {}}

        # Add human-readable helpers
        graph["nodes_desc"] = "List of every atom with extracted entities."
        graph["edges_desc"] = (
            "Links between atoms that share an object, task, emotion, or persona. "
            "Empty list means no explicit overlap was found."
        )

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

    return graph

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
