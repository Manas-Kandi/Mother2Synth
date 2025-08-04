from fastapi import APIRouter, HTTPException
import json

from quality_guard import run_quality_guard

router = APIRouter()


@router.post("/quality-guard/{filename}")
async def run_quality_validation(filename: str, project_slug: str = None):
    """Run comprehensive quality validation for a project file."""
    from dropzone import dropzone_manager

    if not project_slug:
        raise HTTPException(status_code=400, detail="project_slug query param required")

    themes_path = dropzone_manager.get_project_path(project_slug, "graphs") / filename.replace(".pdf", "_themes.json")
    atoms_path = dropzone_manager.get_project_path(project_slug, "atoms") / filename.replace(".pdf", "_atoms.json")
    insights_path = dropzone_manager.get_project_path(project_slug, "graphs") / filename.replace(".pdf", "_insights.json")
    board_path = dropzone_manager.get_project_path(project_slug, "boards") / filename.replace(".pdf", "_board.json")

    try:
        with open(themes_path, "r", encoding="utf-8") as f:
            themes = json.load(f)
        with open(atoms_path, "r", encoding="utf-8") as f:
            atoms = json.load(f)
        with open(insights_path, "r", encoding="utf-8") as f:
            insights = json.load(f)
        with open(board_path, "r", encoding="utf-8") as f:
            board_data = json.load(f)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Required file not found: {e}")

    return run_quality_guard(project_slug, themes, atoms, insights, board_data)
