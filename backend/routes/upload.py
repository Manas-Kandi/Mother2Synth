import os
import shutil
import time
import json
import fitz
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from llm import gemini_model
from paths import (
    DATA_DIR,
    get_upload_path,
    get_cleaned_path,
    get_atoms_path,
    get_annotated_path,
    get_graph_path,
    get_project_path
)

router = APIRouter()
logger = logging.getLogger(__name__)

LLM_PROMPT = """You are a senior UX research assistant.

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
Return only the cleaned, speaker-separated transcript."""


def run_llm_normalizer(raw_text: str) -> str:
    """Use Gemini to clean and structure raw transcript text."""
    if len(raw_text) > 50000:
        print(f"\u26A0\uFE0F Text very long ({len(raw_text)} chars), truncating to 50k")
        raw_text = raw_text[:50000] + "\n\n[... text truncated due to length ...]"
    prompt = LLM_PROMPT.replace("{raw_text}", raw_text)
    for attempt in range(2):
        try:
            print(f"\U0001F9E0 Normalizing attempt {attempt + 1}")
            response = gemini_model.generate_content(prompt)
            result = response.text.strip()
            if result and len(result) > 10:
                print(f"\u2705 Normalization successful ({len(result)} chars)")
                return result
            raise ValueError("Normalizer returned empty or very short result")
        except Exception as e:
            print(f"\u274C Normalization error (attempt {attempt + 1}): {e}")
            if attempt < 1:
                time.sleep(1)
                continue
    print("\U0001F6AB Normalization failed, returning raw text")
    return f"[Normalization failed - returning raw text]\n\n{raw_text}"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    return full_text


@router.post("/upload")
async def upload_pdfs(project_slug: str = Query(...), files: list[UploadFile] = File(...)):
    saved_files: list[str] = []
    for file in files:
        try:
            file_path = get_upload_path(project_slug, file.filename)
            logger.info("Saving upload to %s", os.path.abspath(file_path))
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(file.filename)
        except Exception as e:
            logger.error("Error saving %s: %s", file.filename, e)
            raise HTTPException(status_code=500, detail=str(e))
    return {"message": f"Saved {len(saved_files)} file(s)", "files": saved_files}


@router.post("/normalize")
async def normalize_file(project_slug: str = Query(...), filename: str = Query(...)):
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Must be a PDF file")
    
    cleaned_path = get_cleaned_path(project_slug, filename)
    logger.info("Resolved cleaned path: %s", os.path.abspath(cleaned_path))
    if os.path.exists(cleaned_path):
        with open(cleaned_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}

    pdf_path = get_upload_path(project_slug, filename)
    logger.info("Resolved upload path: %s", os.path.abspath(pdf_path))
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in project '{project_slug}'")

    try:
        raw_text = extract_text_from_pdf(pdf_path)
        cleaned_text = run_llm_normalizer(raw_text)
        with open(cleaned_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        return {"content": cleaned_text}
    except Exception as e:
        logger.error("Normalization failed for %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def list_projects():
    """Return information about projects and their files."""
    projects = {}
    if not os.path.exists(DATA_DIR):
        return {}

    for project_slug in os.listdir(DATA_DIR):
        project_path = get_project_path(project_slug)
        if not os.path.isdir(project_path):
            continue

        upload_path = os.path.join(project_path, 'uploads')
        if not os.path.exists(upload_path):
            continue

        files_in_project = {}
        for filename in os.listdir(upload_path):
            if not filename.lower().endswith(".pdf"):
                continue
            
            files_in_project[filename] = {
                "cleaned": os.path.exists(get_cleaned_path(project_slug, filename)),
                "atoms": os.path.exists(get_atoms_path(project_slug, filename)),
                "annotated": os.path.exists(get_annotated_path(project_slug, filename)),
                "graph": os.path.exists(get_graph_path(project_slug, filename)),
            }
        if files_in_project:
            projects[project_slug] = files_in_project

    logger.info("Projects listed: %s", list(projects.keys()))
    return projects


@router.get("/cached/{stage}/{filename}")
async def get_cached(stage: str, filename: str, project_slug: str = Query(...)):
    """Return cached results for a file if available."""
    paths = {
        "cleaned": get_cleaned_path(project_slug, filename),
        "atoms": get_atoms_path(project_slug, filename),
        "annotated": get_annotated_path(project_slug, filename),
        "graph": get_graph_path(project_slug, filename),
    }
    path = paths.get(stage)
    if not path or not os.path.exists(path):
        logger.error("Cache miss for project=%s, stage=%s, filename=%s", project_slug, stage, filename)
        raise HTTPException(status_code=404, detail="not cached")
    
    logger.info("Returning cached %s from %s", stage, os.path.abspath(path))
    if stage == "cleaned":
        return PlainTextResponse(open(path, encoding="utf-8").read())
    return JSONResponse(json.load(open(path, encoding="utf-8")))


@router.delete("/projects/{project_slug}")
async def delete_project(project_slug: str):
    """Delete an entire project directory and all its contents."""
    try:
        project_path = get_project_path(project_slug)
        logger.info("Deleting project directory %s", os.path.abspath(project_path))
        if os.path.exists(project_path) and os.path.isdir(project_path):
            shutil.rmtree(project_path)
        return {"ok": True, "message": f"Project '{project_slug}' deleted."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Failed to delete project %s: %s", project_slug, e)
        raise HTTPException(status_code=500, detail=str(e))
