import os
import json
import re
import time
import logging
from uuid import uuid4
from typing import List

from fastapi import APIRouter, HTTPException

from llm import gemini_model
from paths import ATOMS_DIR, CLEANED_DIR, UPLOAD_DIR, ANNOTATED_DIR
from routes.upload import extract_text_from_pdf, run_llm_normalizer

router = APIRouter()
logger = logging.getLogger(__name__)

ATOMISER_PROMPT = """You are an “Atomic Evidence Splitter”.\n\nInput: cleaned transcript  \nOutput: JSON list of atoms.\n\nSchema per atom:\n{\n  \"id\": \"<uuid>\",\n  \"speaker\": \"<speaker>\",\n  \"text\": \"<1–3 sentence idea>\",\n  \"context\": \"<±2 sentences for context>\",\n  \"entities\": {\n    \"objects\": [],\n    \"tasks\": [],\n    \"emotions\": []\n  },\n  \"confidence\": \"high|medium|low\"\n}\n\nRules:\n- Cut only at natural idea boundaries.  \n- Never merge speakers.  \n- Entities must appear verbatim in text.  \n- If unsure, mark confidence=low and shorten text.  \n\nReturn ONLY valid JSON. No commentary.\n\nTranscript:\n{transcript}\n"""


def fix_json_syntax(raw_json: str) -> str:
    """Try to fix common JSON syntax issues."""
    return re.sub(r',([\s]*[}\]])', r'\1', raw_json)


def chunk_and_atomise(clean_text: str, source_file: str, chunk_size: int = 8000) -> List[dict]:
    """Split long text into manageable chunks and atomise each."""
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


def run_llm_atomiser(clean_text: str, source_file: str) -> List[dict]:
    """Run the atomiser on text, chunking if necessary."""
    if len(clean_text) > 15000:
        print(f"\U0001F4CF Text too long ({len(clean_text)} chars), chunking...")
        return chunk_and_atomise(clean_text, source_file)
    prompt = ATOMISER_PROMPT.replace("{transcript}", clean_text)
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
                prompt = ATOMISER_PROMPT.replace("{transcript}", clean_text[:10000])
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
        "text": f"[Atomiser failed after 3 attempts. Text length: {len(clean_text)} chars. Last error: JSON parsing failed]",
        "context": "",
        "entities": {"objects": [], "tasks": [], "emotions": []},
        "confidence": "low",
        "source_file": source_file,
    }]


ANNOTATOR_PROMPT = """You are a UX-insight extractor.\n\nReturn JSON:\n\n{\n  \"insights\": [\n    {\"type\": \"<meta-category>\", \"label\": \"<\u22643 words>\", \"weight\": 0.0-1.0}\n  ],\n  \"tags\": [\"keyword1\", \"keyword2\"]\n}\n\nAllowed types & examples\npersona: mobile user | admin | new hire  \npain: login friction | hidden cost | broken flow  \nemotion: annoyance | anxiety | delight  \nroot_cause: validation bug | slow backend  \nimpact: task abandon | time lost  \ncontext: on-the-go | multitasking  \ndevice: Android | iPhone | desktop  \nchannel: web | app | phone call  \nfrequency: daily | weekly | first-time  \nseverity: blocker | minor | workaround exists\n\nRules\n- Emit 0-2 insights per type, \u22648 total  \n- weight = confidence 0-1  \n- labels verbatim when possible  \n- skip any you can’t ground\n\nQuote:\n{atom_text}\n"""


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
        print("annotate_atom error:", e)
        return {"insights": [], "tags": []}


@router.get("/atomise/{filename}")
async def atomise_file(filename: str, project_slug: str = None):
    from dropzone import dropzone_manager
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Must be a PDF file")
    if not project_slug:
        raise HTTPException(status_code=400, detail="project_slug query param required")
    atoms_path = dropzone_manager.get_project_path(project_slug, "atoms") / filename.replace(".pdf", ".json")
    cleaned_path = dropzone_manager.get_project_path(project_slug, "cleaned") / filename.replace(".pdf", ".txt")
    raw_path = dropzone_manager.get_project_path(project_slug, "raw") / filename
    logger.info("Atomise paths: atoms=%s cleaned=%s raw=%s", atoms_path, cleaned_path, raw_path)
    try:
        if atoms_path.exists():
            with open(atoms_path, "r", encoding="utf-8") as f:
                return {"atoms": json.load(f)}
        if cleaned_path.exists():
            with open(cleaned_path, "r", encoding="utf-8") as f:
                clean_text = f.read()
        elif raw_path.exists():
            full_text = extract_text_from_pdf(str(raw_path))
            clean_text = run_llm_normalizer(full_text)
            with open(cleaned_path, "w", encoding="utf-8") as f:
                f.write(clean_text)
        else:
            raise HTTPException(status_code=404, detail=f"Raw PDF not found in DropZone: {raw_path}")
        atoms = run_llm_atomiser(clean_text, filename)
        with open(atoms_path, "w", encoding="utf-8") as f:
            json.dump(atoms, f, indent=2, ensure_ascii=False)
        return {"atoms": atoms}
    except Exception as e:
        logger.error("Atomise failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/annotate")
async def annotate_atoms(atoms: List[dict], filename: str, project_slug: str = None):
    """Annotate atoms and cache the results in DropZone."""
    from dropzone import dropzone_manager
    if not project_slug:
        raise HTTPException(status_code=400, detail="project_slug query param required")
    annotated_path = dropzone_manager.get_project_path(project_slug, "annotated") / filename.replace(".pdf", ".json")
    logger.info("Annotate path: %s", annotated_path)
    try:
        if annotated_path.exists():
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
