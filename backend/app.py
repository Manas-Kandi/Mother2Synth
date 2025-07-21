from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .paths import ensure_dirs
from .routes import upload, atoms, graph, comments

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

app.include_router(upload.router)
app.include_router(atoms.router)
app.include_router(graph.router)
app.include_router(comments.router)
