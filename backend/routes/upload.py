import os
import shutil
import json
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import PlainTextResponse, JSONResponse

from paths import (
    DATA_DIR,
    get_upload_path,
    get_cleaned_path,
    get_atoms_path,
    get_annotated_path,
    get_graph_path,
    get_project_path
)
from shared_utils import run_llm_normalizer, extract_text_from_pdf

router = APIRouter()
logger = logging.getLogger(__name__)

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
