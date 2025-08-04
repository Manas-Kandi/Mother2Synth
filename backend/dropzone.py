"""Simple DropZone path manager."""

from pathlib import Path


class DropZoneManager:
    """Manage DropZone paths for a specific project."""

    def __init__(self, project_slug: str):
        """Initialize manager for a given project."""
        self.project_slug = project_slug
        self.base_path = Path("/DropZone") / project_slug
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_path(self, stage: str, filename: str | None = None) -> Path:
        """Return path for a stage and optional filename.

        Creates the stage directory if it doesn't exist.
        """
        stage_path = self.base_path / stage
        stage_path.mkdir(parents=True, exist_ok=True)
        return stage_path / filename if filename else stage_path

