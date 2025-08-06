"""
LLM Chat Assistant for slugg.e
Interactive AI assistant providing guidance throughout the research synthesis process
"""

import json
import re
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from dataclasses import dataclass, asdict

from paths import get_chat_history_path

@dataclass
class ChatMessage:
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    context: Optional[Dict[str, Any]] = None

class ChatAssistant:
    """Interactive LLM chat assistant for research guidance"""
    
    def __init__(self, project_slug: str):
        self.project_slug = project_slug
        self.logger = logging.getLogger(__name__)
        self.conversation_history: List[ChatMessage] = []
        self.context = {
            'current_stage': 'initial',
            'project_data': {},
            'user_goals': [],
            'pending_questions': []
        }
        self._load_history()

    def _load_history(self):
        history_path = get_chat_history_path(self.project_slug)
        if not os.path.exists(history_path):
            return
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                for msg_data in history_data:
                    msg_data['timestamp'] = datetime.fromisoformat(msg_data['timestamp'])
                    self.conversation_history.append(ChatMessage(**msg_data))
            self.logger.info(f"Loaded {len(self.conversation_history)} messages for {self.project_slug}")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error(f"Failed to load or parse chat history for {self.project_slug}: {e}")

    def _save_history(self):
        history_path = get_chat_history_path(self.project_slug)
        try:
            os.makedirs(os.path.dirname(history_path), exist_ok=True)
            history_data = []
            for msg in self.conversation_history:
                msg_dict = asdict(msg)
                msg_dict['timestamp'] = msg.timestamp.isoformat()
                history_data.append(msg_dict)
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save chat history for {self.project_slug}: {e}")

    def process_message(self, message: str, current_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user message and generate contextual response"""
        
        # Update context
        self.context.update(current_context)
        
        # Add to conversation history
        self.conversation_history.append(ChatMessage(
            role="user",
            content=message,
            timestamp=datetime.now(),
            context=current_context
        ))
        
        # Determine intent and generate response
        intent = self._detect_intent(message)
        response = self._generate_response(message, intent)
        
        # Add assistant response to history
        self.conversation_history.append(ChatMessage(
            role="assistant",
            content=json.dumps(response), # Store dict as string
            timestamp=datetime.now()
        ))
        
        self._save_history()
        return response
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        message_lower = message.lower()
        
        intent_patterns = {
            'explain_theme': [
                r'\bexplain\b.*\btheme\b',
                r'\bwhat\b.*\btheme\b.*\bmean',
                r'\bhelp\b.*\bunderstand\b.*\btheme\b'
            ],
            'suggest_improvement': [
                r'\bhow\b.*\bimprove\b',
                r'\bwhat\b.*\bwrong\b.*\btheme\b',
                r'\bsuggestions?\b.*\btheme\b'
            ],
            'add_evidence': [
                r'\badd\b.*\bevidence\b',
                r'\bmore\b.*\bquotes?\b',
                r'\bfind\b.*\bsupporting\b.*\bquotes?\b'
            ],
            'clarify_methodology': [
                r'\bhow\b.*\btheme\b.*\bcreat\w+',
                r'\bmethodology\b',
                r'\bprocess\b.*\btheme\b.*\bidentification\b'
            ],
            'validate_quality': [
                r'\bgood\b.*\benough\b',
                r'\bquality\b.*\bcheck\b',
                r'\bready\b.*\bpresent\b'
            ],
            'export_share': [
                r'\bexport\b',
                r'\bshare\b.*\bresults\b',
                r'\bpdf\b|\bpowerpoint\b|\bdeck\b'
            ]
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return 'general_question'
    
    def _generate_response(self, message: str, intent: str) -> Dict[str, Any]:
        """Generate contextual response based on intent"""
        
        response_data = {
            'response': '',
            'suggestions': [],
            'actions': [],
            'context': {}
        }
        
        if intent == 'explain_theme':
            return self._explain_theme_response(message)
        elif intent == 'suggest_improvement':
            return self._suggest_improvement_response(message)
        elif intent == 'add_evidence':
            return self._add_evidence_response(message)
        elif intent == 'clarify_methodology':
            return self._clarify_methodology_response(message)
        elif intent == 'validate_quality':
            return self._validate_quality_response(message)
        elif intent == 'export_share':
            return self._export_share_response(message)
        else:
            return self._general_response(message)
    
    def _explain_theme_response(self, message: str) -> Dict[str, Any]:
        """Explain themes and their significance"""
        
        themes = self.context.get('themes', [])
        if not themes:
            return {
                'response': "I don't see any themes identified yet. Once themes are created, I can help explain their meaning and significance based on the evidence.",
                'suggestions': [
                    "Run the theme identification process first",
                    "Review the transcript for patterns",
                    "Consider what participants repeatedly mention"
                ],
                'actions': [
                    {'type': 'run_analysis', 'label': 'Identify Themes'}
                ]
            }
        
        # Extract theme name from message
        theme_name = self._extract_theme_name(message)
        theme = next((t for t in themes if t['name'].lower() == theme_name.lower()), None)
        
        if theme:
            response = f"Theme '{theme['name']}' represents {theme.get('description', 'a pattern in user behavior')}. "
            response += f"It's supported by {len(theme.get('evidence', []))} quotes from {len(set([atom.get('speaker', 'unknown') for atom in theme.get('atoms', [])]))} participants. "
            response += f"The key insight is: {theme.get('insight', 'This theme reveals something important about user needs or behaviors')}."
            
            return {
                'response': response,
                'suggestions': [
                    "Review the supporting quotes to see the evidence",
                    "Consider how this theme relates to your research questions",
                    "Think about potential design implications"
                ],
                'actions': [
                    {'type': 'show_quotes', 'label': 'View Supporting Quotes'},
                    {'type': 'show_participants', 'label': 'See Participant Breakdown'}
                ]
            }
        
        return {
            'response': f"Here are your identified themes: {', '.join([t['name'] for t in themes])}. Which theme would you like me to explain in more detail?",
            'suggestions': [
                "Ask about specific themes",
                "Request explanation of theme relationships",
                "Ask about evidence quality for themes"
            ]
        }
    
    def _suggest_improvement_response(self, message: str) -> Dict[str, Any]:
        """Suggest improvements for themes and analysis"""
        
        themes = self.context.get('themes', [])
        if not themes:
            return {
                'response': "To provide improvement suggestions, I need to see your current themes and evidence. Please run the theme identification process first.",
                'suggestions': [
                    "Ensure each theme has 2+ supporting quotes",
                    "Check that themes represent diverse participant perspectives",
                    "Verify themes are specific, not generic"
                ]
            }
        
        # Analyze theme quality
        suggestions = []
        for theme in themes:
            evidence_count = len(theme.get('evidence', []))
            if evidence_count < 2:
                suggestions.append(f"Theme '{theme['name']}' needs more evidence - add {2 - evidence_count} more supporting quotes")
            
            # Check for generic language
            description = theme.get('description', '').lower()
            if any(generic in description for generic in ['users want', 'people need', 'everyone thinks']):
                suggestions.append(f"Theme '{theme['name']}' description is too generic - make it more specific")
        
        response = "Here are my improvement suggestions:\n"
        for suggestion in suggestions:
            response += f"• {suggestion}\n"
        
        return {
            'response': response,
            'suggestions': suggestions,
            'actions': [
                {'type': 'run_quality_check', 'label': 'Run Quality Validation'},
                {'type': 'add_evidence', 'label': 'Find More Supporting Quotes'}
            ]
        }
    
    def _add_evidence_response(self, message: str) -> Dict[str, Any]:
        """Help find additional supporting evidence"""
        
        atoms = self.context.get('atoms', [])
        themes = self.context.get('themes', [])
        
        if not atoms:
            return {
                'response': "I need the atomized transcript data to help find supporting evidence. Please ensure transcripts are processed and atomized.",
                'suggestions': [
                    "Complete transcript processing",
                    "Ensure atoms are created from cleaned transcripts",
                    "Review atomization quality"
                ]
            }
        
        # Find atoms that could support themes
        theme_name = self._extract_theme_name(message)
        if theme_name:
            relevant_atoms = [atom for atom in atoms 
                            if any(keyword in atom.get('text', '').lower() 
                                 for keyword in theme_name.lower().split())]
            
            response = f"Here are potential supporting quotes for '{theme_name}':\n"
            for atom in relevant_atoms[:3]:
                response += f"• '{atom.get('text', '')[:100]}...' (Speaker: {atom.get('speaker', 'Unknown')})\n"
            
            return {
                'response': response,
                'suggestions': [
                    "Review these quotes for relevance",
                    "Check if quotes truly support the theme",
                    "Ensure diverse participant voices"
                ],
                'actions': [
                    {'type': 'add_quote', 'label': 'Add Selected Quotes'},
                    {'type': 'find_more', 'label': 'Search for More Quotes'}
                ]
            }
        
        return {
            'response': "I can help you find supporting evidence. Which theme needs additional quotes?",
            'suggestions': [
                "Provide theme name",
                "Review existing evidence",
                "Consider participant diversity"
            ]
        }
    
    def _clarify_methodology_response(self, message: str) -> Dict[str, Any]:
        """Explain methodology and process"""
        
        response = """The slugg.e system uses a systematic approach to identify themes from research transcripts:

1. **Atomization**: Break transcripts into atomic units (quotes, statements)
2. **Annotation**: Tag atoms with metadata (speaker, context, sentiment)
3. **Theme Identification**: Use LLM to find patterns across atoms
4. **Evidence Building**: Link supporting quotes to each theme
5. **Quality Validation**: Check for sufficient evidence and diversity
6. **Visualization**: Create interactive board for exploration

Key principles:
- Evidence-based: Every theme must have direct quotes
- Participant diversity: Multiple voices support each theme
- Transparency: Show exactly how themes were derived
- Human oversight: You can review and adjust themes
"""
        
        return {
            'response': response,
            'suggestions': [
                "Review the evidence for each theme",
                "Check participant diversity",
                "Consider if themes answer your research questions"
            ],
            'actions': [
                {'type': 'show_methodology', 'label': 'View Detailed Process'},
                {'type': 'show_evidence', 'label': 'See Evidence Trail'}
            ]
        }
    
    def _validate_quality_response(self, message: str) -> Dict[str, Any]:
        """Validate research quality and readiness"""
        
        # This would integrate with quality_guard.py
        return {
            'response': "I can run a comprehensive quality validation to check if your research synthesis is ready for presentation. This will verify evidence sufficiency, participant diversity, and overall quality.",
            'suggestions': [
                "Each theme should have 2+ supporting quotes",
                "Multiple participants should be represented",
                "Themes should be specific, not generic",
                "Causal claims should be supported by evidence"
            ],
            'actions': [
                {'type': 'run_quality_check', 'label': 'Run Quality Validation'},
                {'type': 'show_report', 'label': 'View Quality Report'}
            ]
        }
    
    def _export_share_response(self, message: str) -> Dict[str, Any]:
        """Help with export and sharing options"""
        
        return {
            'response': "I can help you export your research synthesis in multiple formats for sharing with stakeholders:",
            'suggestions': [
                "PDF report with themes and evidence",
                "Interactive board for exploration",
                "PowerPoint presentation deck",
                "Executive summary document"
            ],
            'actions': [
                {'type': 'export_pdf', 'label': 'Generate PDF Report'},
                {'type': 'export_ppt', 'label': 'Create PowerPoint'},
                {'type': 'share_board', 'label': 'Share Interactive Board'}
            ]
        }
    
    def _general_response(self, message: str) -> Dict[str, Any]:
        """Handle general questions and provide helpful guidance"""
        
        return {
            'response': "I'm here to help you with your UX research synthesis. I can assist with:\n\n• Explaining themes and their significance\n• Suggesting improvements to your analysis\n• Finding additional supporting evidence\n• Clarifying the methodology\n• Validating research quality\n• Helping with export and sharing\n\nWhat would you like to explore?",
            'suggestions': [
                "Ask me to explain specific themes",
                "Request improvement suggestions",
                "Ask about methodology",
                "Request quality validation"
            ]
        }
    
    def _extract_theme_name(self, message: str) -> Optional[str]:
        """Extract theme name from message"""
        themes = self.context.get('themes', [])
        message_lower = message.lower()
        
        for theme in themes:
            if theme['name'].lower() in message_lower:
                return theme['name']
        
        # Look for patterns like "theme X" or "the X theme"
        patterns = [
            r'\btheme\s+(\w+)',
            r'\b(\w+)\s+theme\b',
            r'\b(\w+)\s+theme\b'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(1)
        
        return None
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation"""
        
        return {
            'total_messages': len(self.conversation_history),
            'user_messages': len([m for m in self.conversation_history if m.role == 'user']),
            'assistant_messages': len([m for m in self.conversation_history if m.role == 'assistant']),
            'last_interaction': self.conversation_history[-1].timestamp.isoformat() if self.conversation_history else None,
            'topics_discussed': self._extract_topics()
        }
    
    def _extract_topics(self) -> List[str]:
        """Extract topics from conversation history"""
        topics = []
        
        for message in self.conversation_history:
            content = message.content.lower()
            
            if 'theme' in content:
                topics.append('themes')
            if 'evidence' in content:
                topics.append('evidence')
            if 'quality' in content:
                topics.append('quality')
            if 'methodology' in content:
                topics.append('methodology')
            if 'export' in content or 'share' in content:
                topics.append('export')
        
        return list(set(topics))

# Usage example
def create_chat_assistant(project_slug: str) -> ChatAssistant:
    """Create a new chat assistant instance"""
    return ChatAssistant(project_slug)
