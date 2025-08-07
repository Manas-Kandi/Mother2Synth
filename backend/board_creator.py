"""
Tldraw-based Collaborative Board Creator for slugg.e
Real-time collaborative whiteboard with journey mapping and theme visualization
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from paths import get_stage_path
import asyncio
try:
    from supabase import create_client, Client  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = None
try:
    import y_py as Y  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Y = None

@dataclass
class BoardElement:
    """Base class for board elements"""
    id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    content: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class JourneyStep:
    """Represents a step in the user journey"""
    step_id: str
    title: str
    description: str
    pain_level: str  # red, yellow, green
    emotion: str
    quotes: List[str]
    participants: List[str]
    x: float
    y: float

@dataclass
class ThemeCluster:
    """Represents a theme cluster on the board"""
    cluster_id: str
    theme_name: str
    color: str
    quotes: List[str]
    participants: List[str]
    pain_points: List[str]
    opportunities: List[str]
    x: float
    y: float
    size: float

@dataclass
class OpportunityCard:
    """Represents a design opportunity"""
    card_id: str
    title: str
    description: str
    linked_pain_points: List[str]
    priority: str  # high, medium, low
    effort_estimate: str
    x: float
    y: float

class BoardCreator:
    """Creates and manages collaborative tldraw boards"""
    
    def __init__(self, project_slug: str, supabase_url: str = None, supabase_key: str = None):
        self.project_slug = project_slug
        self.boards_dir = Path(get_stage_path(project_slug, 'boards'))
        self.boards_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Supabase client for persistence
        if supabase_url and supabase_key and create_client:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
        
        # Initialize Yjs document for real-time collaboration if available
        if Y:
            self.ydoc = Y.YDoc()
            self.board_state = self.ydoc.get_map("board")
        else:
            self.ydoc = None
            self.board_state = None
        
    async def create_board(self, themes: List[Dict], atoms: List[Dict], 
                          journey_data: Dict, insights: List[Dict]) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Create a comprehensive research synthesis board
        
        Layout:
        - Left: Journey Map (vertical timeline)
        - Center: Theme Clusters (sticky note groups)
        - Right: Quote Bank (drag-and-drop panel)
        - Bottom: Opportunity Cards
        - Top: Open Questions
        """
        
        board_id = str(uuid.uuid4())[:8]
        board_data = {
            "id": board_id,
            "project_slug": self.project_slug,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "elements": {},
            "layout": {
                "journey_map": {"x": 100, "y": 100, "width": 400, "height": 600},
                "theme_clusters": {"x": 600, "y": 100, "width": 800, "height": 600},
                "quote_bank": {"x": 1500, "y": 100, "width": 300, "height": 600},
                "opportunities": {"x": 100, "y": 750, "width": 1700, "height": 200},
                "questions": {"x": 100, "y": 50, "width": 1700, "height": 50}
            }
        }
        
        # Create journey map
        journey_elements = self._create_journey_map(journey_data)
        
        # Create theme clusters
        theme_elements = self._create_theme_clusters(themes, atoms)
        
        # Create quote bank
        quote_elements = self._create_quote_bank(atoms)
        
        # Create opportunity cards
        opportunity_elements = self._create_opportunity_cards(themes, insights)
        
        # Create open questions
        question_elements = self._create_open_questions(insights)
        
        # Combine all elements
        all_elements = {**journey_elements, **theme_elements, 
                       **quote_elements, **opportunity_elements, **question_elements}
        
        board_data["elements"] = all_elements
        
        # Save to file
        board_file = self.boards_dir / f"{board_id}.json"
        with open(board_file, 'w') as f:
            json.dump(board_data, f, indent=2, default=str)
        
        # Save to Supabase if available
        if self.supabase:
            await self._save_to_supabase(board_data)
        
        # Initialize Yjs document for real-time collaboration if available
        if self.ydoc:
            self._initialize_yjs_board(board_data)
        
        board_url = self.get_board_url(board_id)
        return board_data, board_url
    
    def _create_journey_map(self, journey_data: Dict) -> Dict[str, Any]:
        """Create journey map elements"""
        elements = {}
        
        if not journey_data.get('journey'):
            return elements
        
        y_offset = 150
        step_height = 80
        
        for i, step in enumerate(journey_data['journey']):
            step_id = f"journey_step_{i}"
            
            # Color based on pain level
            pain_color = {
                'red': '#ff4444',
                'yellow': '#ffaa44',
                'green': '#44ff44'
            }.get(step.get('pain', 'yellow'), '#ffaa44')
            
            elements[step_id] = {
                "type": "shape",
                "x": 150,
                "y": y_offset + (i * step_height),
                "width": 350,
                "height": 70,
                "rotation": 0,
                "style": {
                    "color": pain_color,
                    "fill": "solid",
                    "stroke": "#000000",
                    "strokeWidth": 2
                },
                "label": {
                    "text": step.get('step', f'Step {i+1}'),
                    "font": "mono",
                    "size": "small",
                    "color": "#000000"
                },
                "metadata": {
                    "type": "journey_step",
                    "pain_level": step.get('pain'),
                    "emotion": step.get('emotion'),
                    "quotes": step.get('atoms', []),
                    "participants": step.get('participants', [])
                }
            }
        
        return elements
    
    def _create_theme_clusters(self, themes: List[Dict], atoms: List[Dict]) -> Dict[str, Any]:
        """Create theme cluster elements"""
        elements = {}
        
        cluster_width = 200
        cluster_height = 150
        x_start = 600
        y_start = 150
        
        for i, theme in enumerate(themes):
            cluster_id = f"theme_cluster_{i}"
            
            # Position in grid
            row = i // 3
            col = i % 3
            x = x_start + (col * (cluster_width + 20))
            y = y_start + (row * (cluster_height + 20))
            
            # Color based on theme type
            theme_color = self._get_theme_color(theme.get('name', ''))
            
            elements[cluster_id] = {
                "type": "sticky",
                "x": x,
                "y": y,
                "width": cluster_width,
                "height": cluster_height,
                "rotation": 0,
                "style": {
                    "color": theme_color,
                    "fill": "semi",
                    "stroke": "#000000",
                    "strokeWidth": 1
                },
                "label": {
                    "text": theme.get('name', f'Theme {i+1}'),
                    "font": "mono",
                    "size": "medium",
                    "color": "#000000"
                },
                "metadata": {
                    "type": "theme_cluster",
                    "theme_name": theme.get('name'),
                    "quotes": theme.get('atoms', []),
                    "participants": theme.get('participants', []),
                    "pain_points": theme.get('pain_points', []),
                    "opportunities": theme.get('opportunities', [])
                }
            }
            
            # Add individual quote stickies within cluster
            for j, quote in enumerate(theme.get('atoms', [])[:5]):
                quote_id = f"theme_quote_{i}_{j}"
                elements[quote_id] = {
                    "type": "sticky",
                    "x": x + 10,
                    "y": y + 40 + (j * 20),
                    "width": 180,
                    "height": 15,
                    "style": {
                        "color": "#ffffff",
                        "fill": "semi",
                        "stroke": "#cccccc",
                        "strokeWidth": 1
                    },
                    "label": {
                        "text": quote[:50] + "..." if len(quote) > 50 else quote,
                        "font": "mono",
                        "size": "small",
                        "color": "#333333"
                    }
                }
        
        return elements
    
    def _create_quote_bank(self, atoms: List[Dict]) -> Dict[str, Any]:
        """Create quote bank elements"""
        elements = {}
        
        x_start = 1500
        y_start = 150
        quote_height = 60
        
        for i, atom in enumerate(atoms):
            quote_id = f"quote_{i}"
            
            elements[quote_id] = {
                "type": "sticky",
                "x": x_start,
                "y": y_start + (i * quote_height),
                "width": 280,
                "height": 50,
                "style": {
                    "color": "#f0f0f0",
                    "fill": "semi",
                    "stroke": "#999999",
                    "strokeWidth": 1
                },
                "label": {
                    "text": atom.get('text', '')[:100] + "..." if len(atom.get('text', '')) > 100 else atom.get('text', ''),
                    "font": "mono",
                    "size": "small",
                    "color": "#333333"
                },
                "metadata": {
                    "type": "quote",
                    "atom_id": atom.get('id'),
                    "speaker": atom.get('speaker'),
                    "sentiment": atom.get('sentiment'),
                    "tags": atom.get('tags', [])
                }
            }
        
        return elements
    
    def _create_opportunity_cards(self, themes: List[Dict], insights: List[Dict]) -> Dict[str, Any]:
        """Create opportunity card elements"""
        elements = {}
        
        x_start = 100
        y_start = 750
        card_width = 200
        card_height = 120
        
        opportunities = self._extract_opportunities(themes, insights)
        
        for i, opportunity in enumerate(opportunities):
            card_id = f"opportunity_{i}"
            
            x = x_start + (i * (card_width + 20))
            
            elements[card_id] = {
                "type": "card",
                "x": x,
                "y": y_start,
                "width": card_width,
                "height": card_height,
                "style": {
                    "color": "#90EE90",  # Light green
                    "fill": "semi",
                    "stroke": "#228B22",
                    "strokeWidth": 2
                },
                "label": {
                    "text": opportunity.get('title', f'Opportunity {i+1}'),
                    "font": "mono",
                    "size": "medium",
                    "color": "#006400"
                },
                "metadata": {
                    "type": "opportunity",
                    "description": opportunity.get('description'),
                    "priority": opportunity.get('priority'),
                    "effort": opportunity.get('effort'),
                    "linked_pain_points": opportunity.get('linked_pain_points', [])
                }
            }
        
        return elements
    
    def _create_open_questions(self, insights: List[Dict]) -> Dict[str, Any]:
        """Create open question elements"""
        elements = {}
        
        x_start = 100
        y_start = 50
        
        questions = self._extract_open_questions(insights)
        
        for i, question in enumerate(questions):
            question_id = f"question_{i}"
            
            elements[question_id] = {
                "type": "sticky",
                "x": x_start + (i * 250),
                "y": y_start,
                "width": 240,
                "height": 40,
                "style": {
                    "color": "#FFA500",  # Orange
                    "fill": "semi",
                    "stroke": "#FF8C00",
                    "strokeWidth": 2
                },
                "label": {
                    "text": question.get('text', f'Question {i+1}'),
                    "font": "mono",
                    "size": "small",
                    "color": "#8B4513"
                },
                "metadata": {
                    "type": "open_question",
                    "priority": question.get('priority', 'medium')
                }
            }
        
        return elements
    
    def _get_theme_color(self, theme_name: str) -> str:
        """Get color for theme based on name"""
        colors = [
            "#FFB6C1", "#87CEEB", "#98FB98", "#F0E68C", 
            "#DDA0DD", "#F4A460", "#E6E6FA", "#D3D3D3"
        ]
        
        # Use theme name to determine color consistently
        color_index = hash(theme_name) % len(colors)
        return colors[color_index]
    
    def _extract_opportunities(self, themes: List[Dict], insights: List[Dict]) -> List[Dict]:
        """Extract opportunities from themes and insights"""
        opportunities = []
        
        for insight in insights:
            if insight.get('type') == 'opportunity':
                opportunities.append({
                    'title': insight.get('title', 'Untitled Opportunity'),
                    'description': insight.get('description', ''),
                    'priority': insight.get('priority', 'medium'),
                    'effort': insight.get('effort', 'medium'),
                    'linked_pain_points': insight.get('linked_pain_points', [])
                })
        
        # Generate opportunities from pain points
        for theme in themes:
            pain_points = theme.get('pain_points', [])
            for pain in pain_points:
                opportunities.append({
                    'title': f"Address: {pain}",
                    'description': f"Design intervention for {pain}",
                    'priority': 'high',
                    'effort': 'medium',
                    'linked_pain_points': [pain]
                })
        
        return opportunities
    
    def _extract_open_questions(self, insights: List[Dict]) -> List[Dict]:
        """Extract open questions from insights"""
        questions = []
        
        for insight in insights:
            if insight.get('type') == 'question':
                questions.append({
                    'text': insight.get('text', 'Open Question'),
                    'priority': insight.get('priority', 'medium')
                })
        
        return questions
    
    async def _save_to_supabase(self, board_data: Dict):
        """Save board data to Supabase"""
        try:
            await self.supabase.table('boards').upsert({
                'id': board_data['id'],
                'project_slug': board_data['project_slug'],
                'board_data': board_data,
                'created_at': board_data['created_at'],
                'updated_at': board_data['updated_at']
            }).execute()
        except Exception as e:
            print(f"Error saving to Supabase: {e}")
    
    def _initialize_yjs_board(self, board_data: Dict):
        """Initialize Yjs document for real-time collaboration"""
        # Set initial board state
        self.board_state.set('elements', json.dumps(board_data['elements']))
        self.board_state.set('metadata', json.dumps({
            'project_slug': board_data['project_slug'],
            'created_at': board_data['created_at']
        }))
    
    def get_board_url(self, board_id: str) -> str:
        """Get URL for accessing the board"""
        return f"/boards/{self.project_slug}/{board_id}"
    
    def export_board(self, board_id: str, format: str = 'json') -> str:
        """Export board in specified format"""
        board_file = self.boards_dir / f"{board_id}.json"
        
        if not board_file.exists():
            return None
        
        with open(board_file, 'r') as f:
            board_data = json.load(f)
        
        if format == 'pdf':
            # TODO: Implement PDF export
            return f"{board_id}.pdf"
        elif format == 'png':
            # TODO: Implement PNG export
            return f"{board_id}.png"
        else:
            return str(board_file)

# Example usage
async def create_research_board(project_slug: str, themes: List[Dict], 
                               atoms: List[Dict], journey_data: Dict, 
                               insights: List[Dict]) -> Dict[str, Any]:
    """Create a complete research synthesis board"""
    
    creator = BoardCreator(project_slug)
    board_data, board_url = await creator.create_board(themes, atoms, journey_data, insights)
    board_id = board_data.get('id')
    
    return {
        'board_id': board_id,
        'board_url': board_url,
        'export_url': f"/api/export/{board_id}"
    }
