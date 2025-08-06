"""
Quality Guard System for Mother-2
Final validation system ensuring research quality and evidence standards
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class QualityCheck:
    """Individual quality check result"""
    check_name: str
    passed: bool
    score: float
    details: Dict[str, Any]
    recommendations: List[str]
    severity: str  # critical, warning, info

class QualityGuard:
    """Comprehensive quality validation system"""
    
    def __init__(self, project_slug: str):
        self.project_slug = project_slug
        self.logger = logging.getLogger(__name__)
        
    def run_full_validation(self, themes: List[Dict], atoms: List[Dict], 
                          insights: List[Dict], board_data: Dict) -> Dict[str, Any]:
        """Run comprehensive quality validation"""
        
        checks = []
        
        # Evidence validation checks
        checks.extend(self._validate_evidence_sufficiency(themes, atoms))
        checks.extend(self._validate_quote_uniqueness(themes))
        checks.extend(self._validate_participant_diversity(themes, atoms))
        
        # Content quality checks
        checks.extend(self._validate_generic_statements(insights))
        checks.extend(self._validate_causal_statements(themes, atoms))
        checks.extend(self._validate_persona_clarity(themes))
        
        # Technical checks
        checks.extend(self._validate_data_integrity(themes, atoms, insights))
        checks.extend(self._validate_board_completeness(board_data))
        
        # Generate final report
        validation_report = self._generate_validation_report(checks)
        
        return validation_report
    
    def _validate_evidence_sufficiency(self, themes: List[Dict], atoms: List[Dict]) -> List[QualityCheck]:
        """Validate that each theme has sufficient evidence"""
        checks = []
        
        for theme in themes:
            evidence_count = len(theme.get('evidence', []))
            unique_participants = len(set([atom.get('speaker', 'unknown') 
                                         for atom in theme.get('atoms', [])]))
            
            # Check minimum evidence
            min_evidence_check = QualityCheck(
                check_name=f"theme_evidence_{theme['name']}",
                passed=evidence_count >= 2,
                score=min(1.0, evidence_count / 3.0),
                details={
                    'theme': theme['name'],
                    'evidence_count': evidence_count,
                    'required_minimum': 2
                },
                recommendations=[
                    f"Add {2 - evidence_count} more supporting quotes" if evidence_count < 2 else "Evidence sufficient"
                ],
                severity="critical" if evidence_count < 2 else "info"
            )
            checks.append(min_evidence_check)
            
            # Check participant diversity
            diversity_check = QualityCheck(
                check_name=f"theme_diversity_{theme['name']}",
                passed=unique_participants >= 2,
                score=min(1.0, unique_participants / 3.0),
                details={
                    'theme': theme['name'],
                    'unique_participants': unique_participants,
                    'total_quotes': evidence_count
                },
                recommendations=[
                    f"Include perspectives from {2 - unique_participants} more participants" if unique_participants < 2 else "Diversity sufficient"
                ],
                severity="warning" if unique_participants < 2 else "info"
            )
            checks.append(diversity_check)
        
        return checks
    
    def _validate_quote_uniqueness(self, themes: List[Dict]) -> List[QualityCheck]:
        """Validate that quotes are unique and not duplicated"""
        checks = []
        
        all_quotes = []
        for theme in themes:
            all_quotes.extend(theme.get('evidence', []))
        
        # Check for duplicate quotes
        seen_quotes = set()
        duplicate_quotes = []
        
        for quote in all_quotes:
            if quote in seen_quotes:
                duplicate_quotes.append(quote)
            seen_quotes.add(quote)
        
        uniqueness_check = QualityCheck(
            check_name="quote_uniqueness",
            passed=len(duplicate_quotes) == 0,
            score=1.0 if len(duplicate_quotes) == 0 else 0.5,
            details={
                'total_quotes': len(all_quotes),
                'unique_quotes': len(seen_quotes),
                'duplicate_count': len(duplicate_quotes),
                'duplicates': duplicate_quotes[:5]  # Limit for display
            },
            recommendations=[
                "Remove duplicate quotes" if duplicate_quotes else "All quotes are unique"
            ],
            severity="warning" if duplicate_quotes else "info"
        )
        checks.append(uniqueness_check)
        
        return checks
    
    def _validate_participant_diversity(self, themes: List[Dict], atoms: List[Dict]) -> List[QualityCheck]:
        """Validate participant diversity across themes"""
        checks = []
        
        # Count unique participants across all themes
        all_participants = set()
        theme_participants = {}
        
        for theme in themes:
            participants = set()
            for atom in theme.get('atoms', []):
                speaker = atom.get('speaker', 'unknown')
                participants.add(speaker)
                all_participants.add(speaker)
            theme_participants[theme['name']] = participants
        
        # Check overall diversity
        total_participants = len(all_participants)
        diversity_check = QualityCheck(
            check_name="participant_diversity",
            passed=total_participants >= 3,
            score=min(1.0, total_participants / 5.0),
            details={
                'total_unique_participants': total_participants,
                'themes': len(themes),
                'participants_per_theme': {name: len(parts) for name, parts in theme_participants.items()}
            },
            recommendations=[
                f"Include perspectives from {3 - total_participants} more participants" if total_participants < 3 else "Diversity sufficient"
            ],
            severity="warning" if total_participants < 3 else "info"
        )
        checks.append(diversity_check)
        
        return checks
    
    def _validate_generic_statements(self, insights: List[Dict]) -> List[QualityCheck]:
        """Validate against generic or cliché statements"""
        checks = []
        
        generic_patterns = [
            r'\busers want\b',
            r'\bpeople need\b',
            r'\beveryone thinks\b',
            r'\bmost users\b',
            r'\bgenerally speaking\b',
            r'\bit is clear that\b',
            r'\bobviously\b',
            r'\bof course\b',
            r'\bcommon sense\b',
            r'\bas we all know\b'
        ]
        
        generic_insights = []
        for insight in insights:
            text = insight.get('text', '').lower()
            for pattern in generic_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    generic_insights.append({
                        'insight': insight.get('title', 'Untitled'),
                        'pattern': pattern,
                        'text': text[:100] + "..." if len(text) > 100 else text
                    })
        
        generic_check = QualityCheck(
            check_name="generic_statements",
            passed=len(generic_insights) == 0,
            score=1.0 if len(generic_insights) == 0 else 0.7,
            details={
                'generic_insights_count': len(generic_insights),
                'examples': generic_insights[:3]
            },
            recommendations=[
                "Replace generic statements with specific evidence" if generic_insights else "No generic statements found"
            ],
            severity="warning" if generic_insights else "info"
        )
        checks.append(generic_check)
        
        return checks
    
    def _validate_causal_statements(self, themes: List[Dict], atoms: List[Dict]) -> List[QualityCheck]:
        """Validate that causal statements are grounded in evidence"""
        checks = []
        
        causal_patterns = [
            r'\bbecause\b',
            r'\bcauses\b',
            r'\bleads to\b',
            r'\bresults in\b',
            r'\btherefore\b',
            r'\bas a result\b',
            r'\bdue to\b'
        ]
        
        ungrounded_causal = []
        for theme in themes:
            description = theme.get('description', '').lower()
            
            # Check for causal language
            has_causal = any(re.search(pattern, description, re.IGNORECASE) 
                           for pattern in causal_patterns)
            
            if has_causal:
                # Check if evidence supports the causal claim
                evidence_count = len(theme.get('evidence', []))
                supporting_quotes = len([atom for atom in theme.get('atoms', []) 
                                       if any(pattern in atom.get('text', '').lower() 
                                            for pattern in causal_patterns)])
                
                if supporting_quotes < 2:
                    ungrounded_causal.append({
                        'theme': theme['name'],
                        'description': description,
                        'evidence_count': evidence_count,
                        'supporting_quotes': supporting_quotes
                    })
        
        causal_check = QualityCheck(
            check_name="causal_statements",
            passed=len(ungrounded_causal) == 0,
            score=1.0 if len(ungrounded_causal) == 0 else 0.8,
            details={
                'ungrounded_causal_count': len(ungrounded_causal),
                'examples': ungrounded_causal[:2]
            },
            recommendations=[
                "Add supporting evidence for causal claims" if ungrounded_causal else "All causal statements are grounded"
            ],
            severity="warning" if ungrounded_causal else "info"
        )
        checks.append(causal_check)
        
        return checks
    
    def _validate_persona_clarity(self, themes: List[Dict]) -> List[QualityCheck]:
        """Validate against generic personas"""
        checks = []
        
        generic_personas = [
            'busy professional',
            'tech-savvy user',
            'millennial',
            'power user',
            'casual user',
            'average person',
            'typical user',
            'general user'
        ]
        
        generic_persona_usage = []
        for theme in themes:
            description = theme.get('description', '').lower()
            for persona in generic_personas:
                if persona in description:
                    generic_persona_usage.append({
                        'theme': theme['name'],
                        'persona': persona,
                        'context': description[:100] + "..." if len(description) > 100 else description
                    })
        
        persona_check = QualityCheck(
            check_name="persona_clarity",
            passed=len(generic_persona_usage) == 0,
            score=1.0 if len(generic_persona_usage) == 0 else 0.6,
            details={
                'generic_personas_count': len(generic_persona_usage),
                'examples': generic_persona_usage[:3]
            },
            recommendations=[
                "Replace generic personas with specific participant descriptions" if generic_persona_usage else "Personas are specific and grounded"
            ],
            severity="warning" if generic_persona_usage else "info"
        )
        checks.append(persona_check)
        
        return checks
    
    def _validate_data_integrity(self, themes: List[Dict], atoms: List[Dict], 
                               insights: List[Dict]) -> List[QualityCheck]:
        """Validate data integrity and completeness"""
        checks = []
        
        # Check for missing data
        missing_data = []
        
        for theme in themes:
            if not theme.get('name'):
                missing_data.append(f"Theme missing name: {theme}")
            if not theme.get('evidence'):
                missing_data.append(f"Theme missing evidence: {theme.get('name', 'Unknown')}")
        
        for atom in atoms:
            if not atom.get('text'):
                missing_data.append(f"Atom missing text: {atom}")
        
        integrity_check = QualityCheck(
            check_name="data_integrity",
            passed=len(missing_data) == 0,
            score=1.0 if len(missing_data) == 0 else 0.5,
            details={
                'missing_data_count': len(missing_data),
                'issues': missing_data[:5]
            },
            recommendations=[
                "Complete missing data fields" if missing_data else "Data integrity maintained"
            ],
            severity="critical" if missing_data else "info"
        )
        checks.append(integrity_check)
        
        return checks
    
    def _validate_board_completeness(self, board_data: Dict) -> List[QualityCheck]:
        """Validate board completeness"""
        checks = []
        
        required_elements = ['journey_map', 'theme_clusters', 'quote_bank', 'opportunities']
        missing_elements = []
        
        elements = board_data.get('elements', {})
        
        for element_type in required_elements:
            if not any(e.get('metadata', {}).get('type') == element_type 
                      for e in elements.values()):
                missing_elements.append(element_type)
        
        completeness_check = QualityCheck(
            check_name="board_completeness",
            passed=len(missing_elements) == 0,
            score=1.0 if len(missing_elements) == 0 else 0.8,
            details={
                'missing_elements': missing_elements
            },
            recommendations=[
                f"Add missing elements: {', '.join(missing_elements)}" if missing_elements else "Board is complete"
            ],
            severity="warning" if missing_elements else "info"
        )
        checks.append(completeness_check)
        
        return checks
    
    def _generate_validation_report(self, checks: List[QualityCheck]) -> Dict[str, Any]:
        """Generate comprehensive validation report"""
        
        critical_issues = [c for c in checks if c.severity == 'critical' and not c.passed]
        warnings = [c for c in checks if c.severity == 'warning' and not c.passed]
        info_items = [c for c in checks if c.severity == 'info']
        
        overall_score = sum(c.score for c in checks) / len(checks) if checks else 0.0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'project_slug': self.project_slug,
            'overall_score': overall_score,
            'status': 'PASSED' if len(critical_issues) == 0 else 'FAILED',
            'summary': {
                'total_checks': len(checks),
                'passed': len([c for c in checks if c.passed]),
                'failed': len([c for c in checks if not c.passed]),
                'critical_issues': len(critical_issues),
                'warnings': len(warnings)
            },
            'critical_issues': critical_issues,
            'warnings': warnings,
            'info': info_items,
            'recommendations': self._generate_recommendations(critical_issues, warnings),
            'next_steps': self._generate_next_steps(critical_issues, warnings)
        }
    
    def _generate_recommendations(self, critical_issues: List[QualityCheck], 
                                warnings: List[QualityCheck]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for issue in critical_issues:
            recommendations.extend(issue.recommendations)
        
        for warning in warnings:
            recommendations.extend(warning.recommendations)
        
        return list(set(recommendations))  # Remove duplicates
    
    def _generate_next_steps(self, critical_issues: List[QualityCheck], 
                           warnings: List[QualityCheck]) -> List[str]:
        """Generate next steps for fixing issues"""
        next_steps = []
        
        if critical_issues:
            next_steps.append("Address all critical issues before finalizing")
            next_steps.append("Review and enhance evidence for themes with insufficient support")
        
        if warnings:
            next_steps.append("Review warnings and consider improvements")
            next_steps.append("Add more diverse participant perspectives")
            next_steps.append("Replace generic statements with specific evidence")
        
        if not critical_issues and not warnings:
            next_steps.append("Research synthesis meets quality standards")
            next_steps.append("Ready for stakeholder presentation")
        
        return next_steps


