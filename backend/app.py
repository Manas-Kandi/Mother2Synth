import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from paths import ensure_dirs
from routes import upload, atoms, graph, comments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ensure_dirs()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
