import os
import re
import json
import time
import logging
from uuid import uuid4
from typing import List

import fitz
from fastapi import APIRouter, HTTPException, Query, Body

from llm import gemini_model
from paths import get_cleaned_path, get_upload_path, get_atoms_path, get_annotated_path
from shared_utils import run_llm_normalizer, extract_text_from_pdf

router = APIRouter()
logger = logging.getLogger(__name__)


# NOTE: This is duplicated from routes/upload.py. Consider refactoring to a shared utils file.
LLM_PROMPT_NORMALIZER = """You are a senior UX research assistant.

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
"""


ATOMISER_PROMPT = """You are a hyper-granular insight atomiser for UX research.

You will be given a transcript chunk. Your task is to extract every atomic, self-contained insight from the user's speech.

Return a JSON list of objects, where each object is one atomic insight:

[
  {
    "id": "<unique UUID>",
    "speaker": "<speaker name>",
    "text": "<exact user quote, verbatim>",
    "context": "<optional: what was being discussed>",
    "entities": {
      "objects": ["<e.g., 'dashboard', 'login button'>"],
      "tasks": ["<e.g., 'reset password', 'find contact info'>"],
      "emotions": ["<e.g., 'frustration', 'confusion', 'relief'>"]
    },
    "confidence": "<high|medium|low>"
  }
]

Rules:
1.  **Atomicity is KEY**: Each object must represent a single, indivisible idea, observation, or feeling. If a sentence contains two ideas, split it into two atoms.
2.  **Verbatim Quotes**: The `text` field MUST be an exact quote from the transcript.
3.  **Speaker Attribution**: Correctly identify the speaker for each quote.
4.  **Entity Extraction**: Populate the `entities` object. Be specific. If no entities are present, use empty lists.
5.  **Confidence Score**: Rate your confidence in the interpretation of the insight.
6.  **ID Generation**: You MUST generate a unique UUID for the `id` of every atom.
7.  **JSON ONLY**: Output nothing but a valid, parseable JSON list. Do not include markdown backticks or any other text.

Transcript Chunk:
---
{transcript}
---
"""


def fix_json_syntax(raw_json: str) -> str:
    """Attempt to fix common JSON syntax errors from LLM output."""
    # Add missing closing bracket for the list
    if raw_json.strip().endswith("}"):
        raw_json += "]"
    # Add missing closing brace for the last object
    if '"' in raw_json and not raw_json.strip().endswith("}") and not raw_json.strip().endswith("]"):
        raw_json += "}"]"
    # Remove trailing commas
    raw_json = re.sub(r',\s*([}\]])', r'\1', raw_json)
    return raw_json


def chunk_and_atomise(full_text: str, source_file: str) -> List[dict]:
    """Split large text into chunks and atomise each one."""
    lines = full_text.split('\n')
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) > 14000:
            chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    logger.info("Split into %d chunks", len(chunks))
    all_atoms: List[dict] = []
    for i, chunk in enumerate(chunks):
        print(f"\U0001F501 Processing chunk {i + 1}/{len(chunks)}")
        chunk_atoms = run_llm_atomiser_single(chunk, source_file, i + 1)
        all_atoms.extend(chunk_atoms)
        time.sleep(0.5)
    return all_atoms


def run_llm_atomiser_single(chunk_text: str, source_file: str, chunk_num: int) -> List[dict]:
    """Atomise a single chunk of text."""
    prompt = ATOMISER_PROMPT.replace("{transcript}", chunk_text)
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
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
    return []


def run_llm_atomiser(full_text: str, source_file: str) -> List[dict]:
    """Run the atomiser on text, chunking if necessary."""
    if len(full_text) > 15000:
        print(f"\U0001F4CF Text too long ({len(full_text)} chars), chunking...")
        return chunk_and_atomise(full_text, source_file)
    prompt = ATOMISER_PROMPT.replace("{transcript}", full_text)
    for attempt in range(3):
        try:
            response = gemini_model.generate_content(prompt)
            raw = response.text.strip()
            print(f"\U0001F9E0 GEMINI RAW (Atomiser, attempt {attempt + 1}):")
            print(repr(raw[:500]) + ("..." if len(raw) > 500 else ""))
            raw = re.sub(r'^```(?:json)?', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'```$', '', raw, flags=re.MULTILINE)
            raw = raw.strip()
            raw = fix_json_syntax(raw)
            atoms = json.loads(raw)
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
            raise ValueError("No valid atoms found")
        except json.JSONDecodeError as e:
            print(f"\u274C JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                prompt = ATOMISER_PROMPT.replace("{transcript}", full_text[:10000])
                continue
        except Exception as e:
            print(f"\u274C Other error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(1)
                continue
    print("\U0001F6AB All atomisation attempts failed, returning error atom")
    return [{
        "id": str(uuid4()),
        "speaker": "ERROR",
        "text": f"[Atomiser failed after 3 attempts. Text length: {len(full_text)} chars. Last error: JSON parsing failed]",
        "context": "",
        "entities": {"objects": [], "tasks": [], "emotions": []},
        "confidence": "low",
        "source_file": source_file,
    }]


ANNOTATOR_PROMPT = """You are a UX-insight extractor.

You will be given a single atomic insight from a user's speech.

Return a JSON object with the following structure:

{
  "insights": [
    {"type": "<meta-category>", "label": "<3 words>", "weight": 0.0-1.0}
  ],
  "tags": ["keyword1", "keyword2"]
}

Allowed types & examples
persona: mobile user | admin | new hire
pain: login friction | hidden cost | broken flow
emotion: annoyance | anxiety | delight
root_cause: validation bug | slow backend
impact: task abandon | time lost
context: on-the-go | multitasking
device: Android | iPhone | desktop
channel: web | app | phone call
frequency: daily | weekly | first-time
severity: blocker | minor | workaround exists

Rules
- Emit 0-2 insights per type, ≤8 total
- weight = confidence 0-1
- labels verbatim when possible
- skip any you can’t ground

Quote:
{atom_text}
"""


def annotate_atom(text: str) -> dict:
    """Annotate a single atom using the LLM."""
    prompt = ANNOTATOR_PROMPT.replace("{atom_text}", text)
    try:
        response = gemini_model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r'^```(?:json)?|```$', '', raw, flags=re.M).strip()
        payload = json.loads(raw)
        return {
            "insights": payload.get("insights", []),
            "tags": payload.get("tags", []),
        }
    except Exception as e:
        logger.error("annotate_atom error: %s", e)
        return {"insights": [], "tags": []}


@router.post("/atomise")
async def atomise_file(project_slug: str = Query(...), filename: str = Query(...)):
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Must be a PDF file")

    atoms_path = get_atoms_path(project_slug, filename)
    cleaned_path = get_cleaned_path(project_slug, filename)
    upload_path = get_upload_path(project_slug, filename)
    
    logger.info("Atomise paths: atoms=%s cleaned=%s upload=%s", atoms_path, cleaned_path, upload_path)

    try:
        if os.path.exists(atoms_path):
            with open(atoms_path, "r", encoding="utf-8") as f:
                return {"atoms": json.load(f)}

        if os.path.exists(cleaned_path):
            with open(cleaned_path, "r", encoding="utf-8") as f:
                clean_text = f.read()
        elif os.path.exists(upload_path):
            full_text = extract_text_from_pdf(upload_path)
            clean_text = run_llm_normalizer(full_text)
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
        else:
            raise HTTPException(status_code=404, detail=f"Source file not found for project '{project_slug}': {filename}")

        atoms = run_llm_atomiser(clean_text, filename)
        with open(atoms_path, "w", encoding="utf-8") as f:
            json.dump(atoms, f, indent=2, ensure_ascii=False)
        return {"atoms": atoms}
    except Exception as e:
        logger.error("Atomise failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/annotate")
async def annotate_atoms(project_slug: str = Query(...), filename: str = Query(...), atoms: List[dict] = Body(...)):
    """Annotate atoms and cache the results."""
    annotated_path = get_annotated_path(project_slug, filename)
    logger.info("Annotate path: %s", annotated_path)

    try:
        if os.path.exists(annotated_path):
            with open(annotated_path, "r", encoding="utf-8") as f:
                enriched = json.load(f)
        else:
            enriched = []
            for atom in atoms:
                tags = annotate_atom(atom["text"])
                enriched.append({**atom, **tags})
            with open(annotated_path, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=2, ensure_ascii=False)
        return enriched
    except Exception as e:
        logger.error("Annotate failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))
