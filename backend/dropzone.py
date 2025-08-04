"""
Enhanced DropZone system for Mother-2
Handles project-based organization and metadata management
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

class ProjectMetadata(BaseModel):
    """Metadata for research projects"""
    project_id: str
    project_slug: str
    name: str
    description: str
    researcher: str
    created_at: datetime
    updated_at: datetime
    transcript_count: int = 0
    status: str = "active"  # active, processing, completed, archived
    tags: List[str] = []
    settings: Dict = {}

class DropZoneManager:
    """Manages project-based DropZone system"""
    
    def __init__(self, base_path: str = "/DropZone"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.base_path / "projects.json"
        
    def create_project(self, name: str, description: str, researcher: str, 
                      tags: List[str] = None) -> ProjectMetadata:
        """Create a new research project"""
        project_id = str(uuid.uuid4())[:8]
        project_slug = self._generate_slug(name)
        
        metadata = ProjectMetadata(
            project_id=project_id,
            project_slug=project_slug,
            name=name,
            description=description,
            researcher=researcher,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            tags=tags or []
        )
        
        # Create project directory structure
        project_dir = self.base_path / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for each stage
        (project_dir / "raw").mkdir(exist_ok=True)
        (project_dir / "cleaned").mkdir(exist_ok=True)
        (project_dir / "atoms").mkdir(exist_ok=True)
        (project_dir / "annotated").mkdir(exist_ok=True)
        (project_dir / "graphs").mkdir(exist_ok=True)
        (project_dir / "boards").mkdir(exist_ok=True)
        (project_dir / "qa").mkdir(exist_ok=True)
        
        # Save metadata
        self._save_project_metadata(metadata)
        return metadata
    
    def get_project(self, project_slug: str) -> Optional[ProjectMetadata]:
        """Get project metadata by slug"""
        projects = self._load_projects()
        return projects.get(project_slug)
    
    def list_projects(self) -> List[ProjectMetadata]:
        """List all projects"""
        projects = self._load_projects()
        return list(projects.values())
    
    def update_project_status(self, project_slug: str, status: str):
        """Update project status"""
        projects = self._load_projects()
        if project_slug in projects:
            projects[project_slug].status = status
            projects[project_slug].updated_at = datetime.now()
            self._save_projects_metadata(projects)
    
    def get_project_path(self, project_slug: str, stage: str = "raw") -> Path:
        """Get path for specific project and stage"""
        return self.base_path / project_slug / stage
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-friendly slug from name"""
        import re
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def _load_projects(self) -> Dict[str, ProjectMetadata]:
        """Load all project metadata"""
        if not self.projects_file.exists():
            return {}
        
        with open(self.projects_file, 'r') as f:
            data = json.load(f)
            return {
                slug: ProjectMetadata(**metadata) 
                for slug, metadata in data.items()
            }
    
    def _save_project_metadata(self, metadata: ProjectMetadata):
        """Save single project metadata"""
        projects = self._load_projects()
        projects[metadata.project_slug] = metadata
        self._save_projects_metadata(projects)
    
    def _save_projects_metadata(self, projects: Dict[str, ProjectMetadata]):
        """Save all project metadata"""
        with open(self.projects_file, 'w') as f:
            # Convert datetime objects to ISO strings for JSON serialization
            data = {
                slug: {
                    **metadata.dict(),
                    'created_at': metadata.created_at.isoformat(),
                    'updated_at': metadata.updated_at.isoformat()
                }
                for slug, metadata in projects.items()
            }
            json.dump(data, f, indent=2)

# Global DropZone instance
dropzone_manager = DropZoneManager()
