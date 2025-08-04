"""
Enhanced Normalizer for Mother-2
Advanced transcript cleaning with speaker labeling and PII detection
"""

import re
import json
import spacy
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

@dataclass
class NormalizationResult:
    """Result of transcript normalization"""
    cleaned_text: str
    speaker_labels: Dict[str, str]
    metadata: Dict[str, any]
    confidence_scores: Dict[str, float]
    pii_detected: List[Dict[str, str]]
    processing_log: List[str]

class EnhancedNormalizer:
    """Advanced transcript normalizer with AI-powered enhancements"""
    
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for normalization process"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def normalize_transcript(self, raw_text: str, filename: str = None) -> NormalizationResult:
        """
        Comprehensive transcript normalization
        
        Steps:
        1. Text cleaning and standardization
        2. Speaker identification and labeling
        3. PII detection and anonymization
        4. Filler word removal
        5. Confidence scoring
        """
        processing_log = []
        
        # Step 1: Initial text cleaning
        cleaned_text = self._clean_text(raw_text)
        processing_log.append("Initial text cleaning completed")
        
        # Step 2: Speaker identification
        speaker_labels, speaker_confidence = self._identify_speakers(cleaned_text)
        processing_log.append(f"Identified {len(speaker_labels)} unique speakers")
        
        # Step 3: PII detection and anonymization
        pii_detected, anonymized_text = self._detect_and_anonymize_pii(cleaned_text)
        processing_log.append(f"Detected {len(pii_detected)} PII instances")
        
        # Step 4: Advanced cleaning
        final_text = self._advanced_cleaning(anonymized_text)
        processing_log.append("Advanced cleaning completed")
        
        # Step 5: Generate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            speaker_confidence, len(pii_detected), final_text
        )
        
        metadata = {
            "original_length": len(raw_text),
            "cleaned_length": len(final_text),
            "compression_ratio": len(final_text) / len(raw_text) if raw_text else 0,
            "speaker_count": len(speaker_labels),
            "pii_instances": len(pii_detected),
            "filename": filename,
            "processing_timestamp": "2024-08-04T12:00:00Z"
        }
        
        return NormalizationResult(
            cleaned_text=final_text,
            speaker_labels=speaker_labels,
            metadata=metadata,
            confidence_scores=confidence_scores,
            pii_detected=pii_detected,
            processing_log=processing_log
        )
    
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning and standardization"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR/transcription errors
        text = re.sub(r'\b(uh|um|er|like|you know)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(i\.e\.|e\.g\.)\b', lambda m: m.group(0).replace('.', ''), text)
        
        # Standardize punctuation
        text = re.sub(r'([.!?])\1+', r'\1', text)  # Remove duplicate punctuation
        text = re.sub(r'([.!?])\s*([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        
        return text.strip()
    
    def _identify_speakers(self, text: str) -> Tuple[Dict[str, str], float]:
        """AI-powered speaker identification and labeling"""
        speaker_patterns = [
            r'(Speaker \d+):',
            r'(Interviewer \d+):',
            r'(Participant \d+):',
            r'(User \d+):',
            r'(INT|PART|USER):',
            r'(\w+):'  # Generic name-based speakers
        ]
        
        speakers = {}
        speaker_counts = {}
        
        for pattern in speaker_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                speaker_label = match.group(1).strip()
                speakers[speaker_label] = f"Speaker_{len(speakers) + 1}"
                speaker_counts[speaker_label] = speaker_counts.get(speaker_label, 0) + 1
        
        # Calculate confidence based on speaker consistency
        total_speakers = len(speakers)
        total_mentions = sum(speaker_counts.values())
        confidence = min(0.95, total_mentions / (total_speakers * 10)) if total_speakers > 0 else 0.0
        
        return speakers, confidence
    
    def _detect_and_anonymize_pii(self, text: str) -> Tuple[List[Dict], str]:
        """Detect and anonymize personally identifiable information"""
        pii_detected = []
        anonymized_text = text
        
        # Email detection
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        for email in emails:
            pii_detected.append({"type": "email", "original": email, "anonymized": "[EMAIL]"})
            anonymized_text = anonymized_text.replace(email, "[EMAIL]")
        
        # Phone number detection
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, text)
        for phone_parts in phones:
            full_phone = ''.join(phone_parts)
            pii_detected.append({"type": "phone", "original": full_phone, "anonymized": "[PHONE]"})
            anonymized_text = anonymized_text.replace(full_phone, "[PHONE]")
        
        # Name detection using NER
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                pii_detected.append({"type": "name", "original": ent.text, "anonymized": "[NAME]"})
                anonymized_text = anonymized_text.replace(ent.text, "[NAME]")
        
        return pii_detected, anonymized_text
    
    def _advanced_cleaning(self, text: str) -> str:
        """Advanced cleaning with context awareness"""
        # Remove filler words more intelligently
        filler_words = [
            'uh', 'um', 'er', 'like', 'you know', 'sort of', 'kind of',
            'basically', 'actually', 'literally', 'basically'
        ]
        
        for filler in filler_words:
            pattern = r'\b' + filler + r'\b'
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Fix sentence boundaries
        text = re.sub(r'([.!?])\s*(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
        
        # Remove duplicate spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _calculate_confidence_scores(self, speaker_confidence: float, 
                                   pii_count: int, cleaned_text: str) -> Dict[str, float]:
        """Calculate confidence scores for each processing step"""
        
        # Text quality confidence
        text_quality = 1.0 - (cleaned_text.count('[') / len(cleaned_text) * 100 if cleaned_text else 0)
        
        # Speaker identification confidence
        speaker_quality = speaker_confidence
        
        # PII handling confidence
        pii_quality = 1.0 - (pii_count * 0.1)  # Reduce confidence for each PII found
        
        # Overall confidence
        overall = (text_quality + speaker_quality + max(0, pii_quality)) / 3
        
        return {
            "overall": max(0.0, min(1.0, overall)),
            "text_quality": max(0.0, min(1.0, text_quality)),
            "speaker_identification": max(0.0, min(1.0, speaker_quality)),
            "pii_handling": max(0.0, min(1.0, pii_quality))
        }

# Global normalizer instance
enhanced_normalizer = EnhancedNormalizer()
