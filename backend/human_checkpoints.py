"""
Human Checkpoint System for slugg.e
Interactive QA system for human-in-the-loop validation
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class CheckpointType(Enum):
    THEME_QA = "theme_qa"
    ANNOTATION_REVIEW = "annotation_review"
    PII_VERIFICATION = "pii_verification"
    FINAL_REVIEW = "final_review"

@dataclass
class ClarifyingQuestion:
    """A single clarifying question for human review"""
    question_id: str
    checkpoint_type: CheckpointType
    context: str
    question: str
    options: List[str]
    current_answer: Optional[str] = None
    confidence_score: float = 0.0
    created_at: datetime = None
    answered_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class HumanCheckpointManager:
    """Manages human checkpoints throughout the research process"""
    
    def __init__(self, project_slug: str):
        self.project_slug = project_slug
        self.checkpoint_dir = f"/DropZone/{project_slug}/qa"
        self.questions: List[ClarifyingQuestion] = []
        self.load_existing_questions()
    
    def generate_theme_questions(self, themes: List[Dict], atoms: List[Dict]) -> List[ClarifyingQuestion]:
        """Generate clarifying questions based on theme analysis"""
        questions = []
        
        # Question 1: Theme clarity
        for theme in themes:
            if len(theme.get('atoms', [])) < 3:
                questions.append(ClarifyingQuestion(
                    question_id=f"theme_clarity_{theme['name']}",
                    checkpoint_type=CheckpointType.THEME_QA,
                    context=f"Theme '{theme['name']}' has only {len(theme.get('atoms', []))} supporting quotes",
                    question=f"Should the theme '{theme['name']}' be merged with another theme or expanded?",
                    options=["Merge with similar theme", "Keep as separate theme", "Remove theme", "Find more supporting quotes"]
                ))
        
        # Question 2: Conflicting themes
        theme_conflicts = self._identify_conflicting_themes(themes, atoms)
        for conflict in theme_conflicts:
            questions.append(ClarifyingQuestion(
                question_id=f"conflict_{conflict['theme1']}_{conflict['theme2']}",
                checkpoint_type=CheckpointType.THEME_QA,
                context=f"Quotes support both '{conflict['theme1']}' and '{conflict['theme2']}' themes",
                question=f"How should we handle the overlap between '{conflict['theme1']}' and '{conflict['theme2']}'?",
                options=["Merge themes", "Split quotes more clearly", "Keep both themes", "Redefine theme boundaries"]
            ))
        
        # Question 3: Underrepresented perspectives
        underrepresented = self._identify_underrepresented_voices(atoms, themes)
        if underrepresented:
            questions.append(ClarifyingQuestion(
                question_id="underrepresented_voices",
                checkpoint_type=CheckpointType.THEME_QA,
                context=f"Some participant perspectives seem underrepresented in current themes",
                question="Should we create themes for underrepresented perspectives or adjust existing themes?",
                options=["Create new themes", "Adjust existing themes", "Add more diverse quotes", "Current representation is sufficient"]
            ))
        
        return questions
    
    def generate_annotation_questions(self, annotations: List[Dict], atoms: List[Dict]) -> List[ClarifyingQuestion]:
        """Generate questions about annotation accuracy"""
        questions = []
        
        # Question 1: Low confidence annotations
        low_confidence_annotations = [ann for ann in annotations if ann.get('confidence', 1.0) < 0.7]
        for annotation in low_confidence_annotations:
            questions.append(ClarifyingQuestion(
                question_id=f"low_confidence_{annotation['id']}",
                checkpoint_type=CheckpointType.ANNOTATION_REVIEW,
                context=f"Annotation for '{annotation['tag']}' has low confidence ({annotation.get('confidence', 0):.2f})",
                question=f"Should this annotation be corrected for the quote: '{annotation['text'][:100]}...'?",
                options=["Correct annotation", "Remove annotation", "Keep as-is", "Get more context"]
            ))
        
        # Question 2: Inconsistent tagging
        inconsistent_tags = self._identify_inconsistent_tagging(annotations)
        for inconsistency in inconsistent_tags:
            questions.append(ClarifyingQuestion(
                question_id=f"inconsistent_{inconsistency['tag']}",
                checkpoint_type=CheckpointType.ANNOTATION_REVIEW,
                context=f"Tag '{inconsistency['tag']}' is applied inconsistently",
                question=f"How should we standardize the use of '{inconsistency['tag']}'?",
                options=["Apply consistently", "Split into more specific tags", "Remove ambiguous tag", "Review all instances"]
            ))
        
        return questions
    
    def generate_pii_questions(self, pii_detected: List[Dict]) -> List[ClarifyingQuestion]:
        """Generate questions about PII handling"""
        questions = []
        
        for pii in pii_detected:
            questions.append(ClarifyingQuestion(
                question_id=f"pii_{pii['type']}_{hash(pii['original'])}",
                checkpoint_type=CheckpointType.PII_VERIFICATION,
                context=f"Detected {pii['type']}: {pii['original']}",
                question=f"How should we handle this {pii['type']}?",
                options=["Anonymize completely", "Partial redaction", "Keep as-is (public info)", "Remove entirely"]
            ))
        
        return questions
    
    def generate_final_review_questions(self, themes: List[Dict], insights: List[Dict]) -> List[ClarifyingQuestion]:
        """Generate final review questions"""
        questions = []
        
        # Question 1: Evidence sufficiency
        weak_themes = [t for t in themes if len(t.get('evidence', [])) < 2]
        for theme in weak_themes:
            questions.append(ClarifyingQuestion(
                question_id=f"evidence_{theme['name']}",
                checkpoint_type=CheckpointType.FINAL_REVIEW,
                context=f"Theme '{theme['name']}' has insufficient evidence",
                question=f"This theme needs more supporting evidence. How should we proceed?",
                options=["Find more quotes", "Merge with stronger theme", "Mark as hypothesis", "Remove theme"]
            ))
        
        # Question 2: Generic statements
        generic_insights = self._identify_generic_statements(insights)
        for insight in generic_insights:
            questions.append(ClarifyingQuestion(
                question_id=f"generic_{insight['id']}",
                checkpoint_type=CheckpointType.FINAL_REVIEW,
                context=f"Insight appears generic: '{insight['text'][:100]}...'",
                question=f"This insight seems generic. Should we:",
                options=["Add specific examples", "Remove generic statement", "Keep as context", "Reword to be more specific"]
            ))
        
        return questions
    
    def _identify_conflicting_themes(self, themes: List[Dict], atoms: List[Dict]) -> List[Dict]:
        """Identify themes with conflicting evidence"""
        conflicts = []
        
        for i, theme1 in enumerate(themes):
            for theme2 in themes[i+1:]:
                # Check for overlapping atoms
                theme1_atoms = set(theme1.get('atoms', []))
                theme2_atoms = set(theme2.get('atoms', []))
                
                overlap = theme1_atoms.intersection(theme2_atoms)
                if len(overlap) > 0:
                    conflicts.append({
                        'theme1': theme1['name'],
                        'theme2': theme2['name'],
                        'overlap_count': len(overlap),
                        'overlapping_atoms': list(overlap)
                    })
        
        return conflicts
    
    def _identify_underrepresented_voices(self, atoms: List[Dict], themes: List[Dict]) -> List[Dict]:
        """Identify participant voices that may be underrepresented"""
        # This is a simplified implementation - would use more sophisticated analysis
        speaker_counts = {}
        for atom in atoms:
            speaker = atom.get('speaker', 'unknown')
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        
        # Find speakers with significantly fewer contributions
        avg_contributions = sum(speaker_counts.values()) / len(speaker_counts) if speaker_counts else 0
        underrepresented = [
            {'speaker': speaker, 'count': count}
            for speaker, count in speaker_counts.items()
            if count < avg_contributions * 0.5
        ]
        
        return underrepresented
    
    def _identify_inconsistent_tagging(self, annotations: List[Dict]) -> List[Dict]:
        """Identify inconsistent application of tags"""
        # Simplified implementation
        tag_usage = {}
        for annotation in annotations:
            tag = annotation.get('tag')
            if tag not in tag_usage:
                tag_usage[tag] = []
            tag_usage[tag].append(annotation)
        
        # Look for tags applied to very different contexts
        inconsistencies = []
        for tag, annotations in tag_usage.items():
            if len(annotations) > 5:  # Only check tags with multiple uses
                # Simple heuristic: check if contexts are very different
                contexts = [ann.get('context', '') for ann in annotations]
                if len(set(contexts[:3])) > 2:  # First few contexts are very different
                    inconsistencies.append({
                        'tag': tag,
                        'annotations': annotations
                    })
        
        return inconsistencies
    
    def _identify_generic_statements(self, insights: List[Dict]) -> List[Dict]:
        """Identify potentially generic or cliché statements"""
        generic_patterns = [
            r'users want',
            r'people need',
            r'everyone thinks',
            r'most users',
            r'generally speaking',
            r'it is clear that',
            r'obviously',
            r'of course'
        ]
        
        generic_insights = []
        for insight in insights:
            text = insight.get('text', '').lower()
            for pattern in generic_patterns:
                if re.search(pattern, text):
                    generic_insights.append(insight)
                    break
        
        return generic_insights
    
    def save_questions(self, questions: List[ClarifyingQuestion]):
        """Save questions to project QA directory"""
        self.questions.extend(questions)
        
        # Save to JSON file
        qa_file = f"{self.checkpoint_dir}/questions.json"
        os.makedirs(os.path.dirname(qa_file), exist_ok=True)
        
        with open(qa_file, 'w') as f:
            json.dump([
                {
                    'question_id': q.question_id,
                    'checkpoint_type': q.checkpoint_type.value,
                    'context': q.context,
                    'question': q.question,
                    'options': q.options,
                    'current_answer': q.current_answer,
                    'confidence_score': q.confidence_score,
                    'created_at': q.created_at.isoformat(),
                    'answered_at': q.answered_at.isoformat() if q.answered_at else None
                }
                for q in self.questions
            ], f, indent=2)
    
    def load_existing_questions(self):
        """Load existing questions from project"""
        qa_file = f"{self.checkpoint_dir}/questions.json"
        if os.path.exists(qa_file):
            with open(qa_file, 'r') as f:
                data = json.load(f)
                self.questions = [
                    ClarifyingQuestion(
                        question_id=q['question_id'],
                        checkpoint_type=CheckpointType(q['checkpoint_type']),
                        context=q['context'],
                        question=q['question'],
                        options=q['options'],
                        current_answer=q.get('current_answer'),
                        confidence_score=q.get('confidence_score', 0.0),
                        created_at=datetime.fromisoformat(q['created_at']),
                        answered_at=datetime.fromisoformat(q['answered_at']) if q.get('answered_at') else None
                    )
                    for q in data
                ]
    
    def get_pending_questions(self) -> List[ClarifyingQuestion]:
        """Get all unanswered questions"""
        return [q for q in self.questions if q.current_answer is None]
    
    def answer_question(self, question_id: str, answer: str):
        """Record an answer to a clarifying question"""
        for question in self.questions:
            if question.question_id == question_id:
                question.current_answer = answer
                question.answered_at = datetime.now()
                break
        
        # Save updated questions
        self.save_questions(self.questions)

# Example usage and integration
async def run_human_checkpoint(project_slug: str, checkpoint_data: Dict):
    """Run a human checkpoint with generated questions"""
    manager = HumanCheckpointManager(project_slug)
    
    # Generate questions based on checkpoint type
    questions = []
    
    if checkpoint_data.get('type') == 'theme_qa':
        questions = manager.generate_theme_questions(
            checkpoint_data.get('themes', []),
            checkpoint_data.get('atoms', [])
        )
    elif checkpoint_data.get('type') == 'annotation_review':
        questions = manager.generate_annotation_questions(
            checkpoint_data.get('annotations', []),
            checkpoint_data.get('atoms', [])
        )
    elif checkpoint_data.get('type') == 'final_review':
        questions = manager.generate_final_review_questions(
            checkpoint_data.get('themes', []),
            checkpoint_data.get('insights', [])
        )
    
    # Save questions
    manager.save_questions(questions)
    
    return {
        'questions': questions,
        'pending_count': len(manager.get_pending_questions()),
        'checkpoint_url': f"/qa/{project_slug}"
    }
