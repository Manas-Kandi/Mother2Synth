import os

# Directory constants
UPLOAD_DIR = "uploads"
CLEANED_DIR = "cleaned"
ATOMS_DIR = "atoms"
ANNOTATED_DIR = "annotated"
GRAPH_DIR = "graph"
COMMENTS_DIR = "data/comments"

def ensure_dirs() -> None:
    """Create required folders if they do not exist."""
    for path in [UPLOAD_DIR, CLEANED_DIR, ATOMS_DIR, ANNOTATED_DIR, GRAPH_DIR, COMMENTS_DIR]:
        os.makedirs(path, exist_ok=True)
