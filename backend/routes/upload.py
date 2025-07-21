import os
import shutil
import time
import json
import fitz
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse

from ..llm import gemini_model
from ..paths import UPLOAD_DIR, CLEANED_DIR, ATOMS_DIR, ANNOTATED_DIR, GRAPH_DIR

router = APIRouter()

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
async def upload_pdfs(files: list[UploadFile] = File(...)):
    saved_files: list[str] = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)
    print("Saved files:", saved_files)
    return {"message": f"Saved {len(saved_files)} file(s)", "files": saved_files}


@router.get("/normalize/{filename}")
async def normalize_file(filename: str):
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Must be a PDF file")
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


@router.get("/projects")
async def list_projects():
    """Return information about uploaded PDF projects."""
    projects = {}
    for filename in os.listdir(UPLOAD_DIR):
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


@router.get("/cached/{stage}/{filename}")
async def get_cached(stage: str, filename: str):
    """Return cached results for a file if available."""
    base = filename.replace(".pdf", "")
    paths = {
        "cleaned": os.path.join(CLEANED_DIR, f"{base}.txt"),
        "atoms": os.path.join(ATOMS_DIR, f"{base}.json"),
        "annotated": os.path.join(ANNOTATED_DIR, f"{base}.json"),
        "graph": os.path.join(GRAPH_DIR, f"{base}.json"),
    }
    path = paths.get(stage)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="not cached")
    if stage == "cleaned":
        return PlainTextResponse(open(path, encoding="utf-8").read())
    return JSONResponse(json.load(open(path, encoding="utf-8")))


@router.delete("/projects/{filename}")
async def delete_project(filename: str):
    """Delete all cached files for a project."""
    base = filename.replace(".pdf", "")
    files_to_delete = [
        os.path.join(UPLOAD_DIR, filename),
        os.path.join(CLEANED_DIR, f"{base}.txt"),
        os.path.join(ATOMS_DIR, f"{base}.json"),
        os.path.join(ANNOTATED_DIR, f"{base}.json"),
        os.path.join(GRAPH_DIR, f"{base}.json"),
    ]
    for path in files_to_delete:
        if os.path.exists(path):
            os.remove(path)
    return {"ok": True}
