from fastapi import APIRouter, HTTPException, Query, Request

from human_checkpoints import HumanCheckpointManager, ClarifyingQuestion

router = APIRouter()


def _serialize_question(question: ClarifyingQuestion) -> dict:
    """Convert a ClarifyingQuestion to a JSON-serializable dict."""
    return {
        "question_id": question.question_id,
        "checkpoint_type": question.checkpoint_type.value,
        "context": question.context,
        "question": question.question,
        "options": question.options,
        "current_answer": question.current_answer,
        "confidence_score": question.confidence_score,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "answered_at": question.answered_at.isoformat() if question.answered_at else None,
    }


@router.get("/qa")
async def get_questions(project_slug: str = Query(...), filename: str | None = Query(None)):
    """Return all pending clarifying questions for a project."""
    manager = HumanCheckpointManager(project_slug)
    pending = manager.get_pending_questions()
    return {"questions": [_serialize_question(q) for q in pending]}


@router.post("/qa/answer")
async def answer_question(request: Request, project_slug: str = Query(...)):
    """Record an answer for a clarifying question."""
    data = await request.json()
    question_id = data.get("question_id")
    answer = data.get("answer")
    if not question_id or answer is None:
        raise HTTPException(status_code=400, detail="question_id and answer required")

    manager = HumanCheckpointManager(project_slug)
    if not any(q.question_id == question_id for q in manager.questions):
        raise HTTPException(status_code=404, detail="question not found")

    manager.answer_question(question_id, answer)
    return {"status": "ok"}
