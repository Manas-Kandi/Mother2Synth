from fastapi import APIRouter, HTTPException, Request

from chat_assistant import ChatAssistant

router = APIRouter()


@router.post("/chat")
async def chat_with_assistant(request: Request):
    """Chat with the LLM research assistant."""
    data = await request.json()
    message = data.get("message")
    project_slug = data.get("project_slug")
    context = data.get("context", {})

    if not message or not project_slug:
        raise HTTPException(status_code=400, detail="message and project_slug required")

    assistant = ChatAssistant(project_slug)
    return assistant.process_message(message, context)


@router.get("/chat/history")
async def get_chat_history(project_slug: str = None):
    """Get chat conversation history."""
    if not project_slug:
        raise HTTPException(status_code=400, detail="project_slug query param required")
    assistant = ChatAssistant(project_slug)
    return assistant.get_conversation_summary()
