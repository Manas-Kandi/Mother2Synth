import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from paths import ensure_dirs
from routes import upload, atoms, graph, comments, quality_guard, chat, board

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ensure_dirs()

app = FastAPI()

# Configure CORS to allow requests from the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",  # Add the port your frontend is running on
        "http://127.0.0.1:5174",  # Also allow 127.0.0.1 for consistency
    ],
    allow_origin_regex=r"http://localhost:517\d$",  # Allow any port starting with 517
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_credentials=True,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON errors and log them."""
    logger.error("Unhandled error at %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})

app.include_router(upload.router)
app.include_router(atoms.router)
app.include_router(graph.router)
app.include_router(comments.router)
app.include_router(quality_guard.router)
app.include_router(chat.router)
app.include_router(board.router)
