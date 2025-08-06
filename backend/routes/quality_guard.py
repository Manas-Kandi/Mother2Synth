import json
import logging
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from quality_guard import QualityGuard
from paths import get_quality_report_path

router = APIRouter()
logger = logging.getLogger(__name__)

class QualityGuardRequest(BaseModel):
    project_slug: str
    themes: List[Dict[str, Any]]
    atoms: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    board_data: Dict[str, Any]

@router.post("/quality-guard")
async def run_quality_validation(request: QualityGuardRequest = Body(...)):
    """Run a comprehensive quality validation on the project synthesis."""
    try:
        guard = QualityGuard(request.project_slug)
        validation_report = guard.run_full_validation(
            themes=request.themes,
            atoms=request.atoms,
            insights=request.insights,
            board_data=request.board_data
        )

        # Save the validation report to the project's quality directory
        report_path = get_quality_report_path(request.project_slug)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, default=str)
        
        logger.info(f"Quality report for {request.project_slug} saved to {report_path}")
        return validation_report
    except Exception as e:
        logger.error(f"Quality guard validation failed for {request.project_slug}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run quality validation: {str(e)}")

