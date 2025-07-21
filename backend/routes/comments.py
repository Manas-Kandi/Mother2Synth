import os
import json
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..paths import COMMENTS_DIR

router = APIRouter()


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


os.makedirs(COMMENTS_DIR, exist_ok=True)


def get_comments_file(filename: str) -> str:
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return os.path.join(COMMENTS_DIR, f"{safe_filename}.json")


def load_comments(filename: str) -> Dict:
    comments_file = get_comments_file(filename)
    if os.path.exists(comments_file):
        with open(comments_file, "r") as f:
            return json.load(f)
    return {"comments": {}, "metadata": {"filename": filename, "created": datetime.now().isoformat()}}


def save_comments(filename: str, comments_data: Dict) -> None:
    comments_file = get_comments_file(filename)
    comments_data["metadata"]["updated"] = datetime.now().isoformat()
    with open(comments_file, "w") as f:
        json.dump(comments_data, f, indent=2)


@router.get("/comments/{filename}")
async def get_comments(filename: str):
    try:
        return load_comments(filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load comments: {str(e)}")


@router.post("/comments/{filename}")
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


@router.delete("/comments/{filename}/{comment_id}")
async def delete_comment(filename: str, comment_id: int) -> CommentResponse:
    try:
        comments_data = load_comments(filename)
        found = False
        for exchange_id, comments_list in comments_data["comments"].items():
            original_length = len(comments_list)
            comments_data["comments"][exchange_id] = [c for c in comments_list if c["id"] != comment_id]
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


@router.get("/comments/{filename}/export")
async def export_comments(filename: str):
    try:
        comments_data = load_comments(filename)
        synthesis_format = {
            "filename": filename,
            "total_comments": sum(len(comments) for comments in comments_data["comments"].values()),
            "insights": [],
            "quotes": [],
        }
        for exchange_id, comments_list in comments_data["comments"].items():
            for comment in comments_list:
                synthesis_format["insights"].append({
                    "exchange_id": int(exchange_id),
                    "text": comment["text"],
                    "author": comment["author"],
                    "timestamp": comment["timestamp"],
                    "quoted_text": comment["selectedText"],
                })
                synthesis_format["quotes"].append({
                    "text": comment["selectedText"],
                    "context": f"Exchange {exchange_id}",
                    "insight": comment["text"],
                    "author": comment["author"],
                })
        return synthesis_format
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export comments: {str(e)}")


@router.get("/synthesis/{filename}/comments")
async def get_synthesis_comments(filename: str):
    return await export_comments(filename)
