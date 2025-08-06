from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import logging

from board_creator import BoardCreator

router = APIRouter(prefix="/board", tags=["board"])
logger = logging.getLogger(__name__)


class BoardPayload(BaseModel):
    themes: List[Dict[str, Any]] = Field(default_factory=list)
    atoms: List[Dict[str, Any]] = Field(default_factory=list)
    journey_data: Dict[str, Any] = Field(default_factory=dict)
    insights: List[Dict[str, Any]] = Field(default_factory=list)


# Accept both /board and /board/create for flexibility
@router.post("/create")
@router.post("/")
async def create_board(
    payload: BoardPayload,
    project_slug: str = Query(..., description="Project identifier"),
):
    """Create a collaborative board for the given project.
    Returns the board data and an optional URL for collaborative access.
    """
    try:
        creator = BoardCreator(project_slug)
        board_data, board_url = await creator.create_board(
            payload.themes,
            payload.atoms,
            payload.journey_data,
            payload.insights,
        )
        response = {"board": board_data}
        if board_url:
            response["board_url"] = board_url
        return response
    except Exception as e:
        logger.exception("Board creation failed for project %s: %s", project_slug, e)
        raise HTTPException(status_code=500, detail=str(e))
