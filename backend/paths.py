import os
import re
from datetime import datetime

# The root directory for all persistent application data.
# All projects and their associated files will be stored here.
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

def ensure_dirs():
    """Ensure that the base data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def sanitize_slug(slug: str) -> str:
    """
    Sanitizes a string to be used as a safe directory name.
    - Converts to lowercase.
    - Replaces spaces and underscores with hyphens.
    - Removes all characters that are not alphanumeric or hyphens.
    - Prevents leading/trailing hyphens and multiple hyphens in a row.
    """
    if not isinstance(slug, str):
        return ""
    slug = slug.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug

def get_project_path(project_slug: str) -> str:
    """
    Returns the absolute path for a given project slug, creating it if it doesn't exist.
    """
    sanitized = sanitize_slug(project_slug)
    if not sanitized:
        raise ValueError("Project slug is empty or invalid after sanitization.")
    
    path = os.path.join(DATA_DIR, sanitized)
    os.makedirs(path, exist_ok=True)
    return path

def get_stage_path(project_slug: str, stage: str) -> str:
    """
    Returns the path for a specific stage within a project (e.g., 'uploads', 'cleaned').
    """
    project_path = get_project_path(project_slug)
    stage_path = os.path.join(project_path, stage)
    os.makedirs(stage_path, exist_ok=True)
    return stage_path

def get_upload_path(project_slug: str, filename: str) -> str:
    """Returns the full path for an uploaded file within its project."""
    return os.path.join(get_stage_path(project_slug, 'uploads'), filename)

def get_cleaned_path(project_slug: str, filename: str) -> str:
    """Returns the full path for a cleaned transcript within its project."""
    base, _ = os.path.splitext(filename)
    return os.path.join(get_stage_path(project_slug, 'cleaned'), f"{base}.txt")

def get_atoms_path(project_slug: str, filename: str) -> str:
    """Returns the full path for an atoms JSON file within its project."""
    base, _ = os.path.splitext(filename)
    return os.path.join(get_stage_path(project_slug, 'atoms'), f"{base}.json")

def get_annotated_path(project_slug: str, filename: str) -> str:
    """Get the absolute path for an annotated atoms file in a project."""
    safe_slug = sanitize_slug(project_slug)
    base_name = os.path.splitext(filename)[0]
    return os.path.join(DATA_DIR, safe_slug, "annotated", f"{base_name}.json")

def get_chat_history_path(project_slug: str) -> str:
    """Get the absolute path for a project's chat history file."""
    safe_slug = sanitize_slug(project_slug)
    return os.path.join(DATA_DIR, safe_slug, "chat", "history.json")

def get_graph_path(project_slug: str, filename: str) -> str:
    """Returns the full path for a graph JSON file within its project."""
    base, _ = os.path.splitext(filename)
    return os.path.join(get_stage_path(project_slug, 'graph'), f"{base}.json")

def get_comments_path(project_slug: str, filename: str) -> str:
    """Returns the full path for a comments JSON file within its project."""
    base, _ = os.path.splitext(filename)
    return os.path.join(get_stage_path(project_slug, 'comments'), f"{base}.json")

def get_quality_report_path(project_slug: str) -> str:
    """Get the absolute path for a project's quality report file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(get_stage_path(project_slug, 'quality'), f"report_{timestamp}.json")
