"""
MedDesk AI - Sentiment Analysis & Escalation Detection
Detects patient frustration and automatically escalates to human staff
"""
from textblob import TextBlob
from typing import Dict, Tuple
from loguru import logger
import re


class SentimentAnalyzer:
    """Real-time sentiment analysis for patient conversations"""

    FRUSTRATION_KEYWORDS = [
        "frustrated", "angry", "unacceptable", "terrible", "worst",
        "horrible", "disappointed", "ridiculous", "stupid", "waste",
        "useless", "incompetent", "furious", "outraged", "disgusted",
        "not helpful", "waste of time", "speak to manager", "supervisor",
        "complaint", "report you", "lawyer", "sue", "legal action"
    ]

    ESCALATION_TRIGGERS = [
        "speak to human", "talk to person", "real person", "human agent",
        "connect me to", "transfer me", "manager", "supervisor",
        "doctor", "nurse", "emergency", "urgent", "help me please",
        "i need help", "this is urgent"
    ]

    POSITIVE_KEYWORDS = [
        "thank you", "thanks", "helpful", "great", "excellent",
        "perfect", "wonderful", "appreciate", "awesome", "fantastic"
    ]

    def __init__(self, escalation_threshold: float = 0.7):
        self.escalation_threshold = escalation_threshold

    def analyze(self, text: str) -> Dict:
        """Comprehensive sentiment analysis"""
        # TextBlob sentiment
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1

        # Custom scoring
        text_lower = text.lower()
        frustration_score = self._calculate_frustration_score(text_lower)
        escalation_score = self._calculate_escalation_score(text_lower)
        urgency_score = self._calculate_urgency_score(text_lower)

        # Overall risk score (0-1)
        risk_score = min(1.0, (
            (1 - polarity) * 0.3 +  # Negative sentiment
            frustration_score * 0.3 +
            escalation_score * 0.3 +
            urgency_score * 0.1
        ))

        # Determine sentiment label
        if polarity > 0.3:
            sentiment_label = "positive"
        elif polarity < -0.3:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        # Should escalate?
        should_escalate = risk_score >= self.escalation_threshold or escalation_score > 0.5

        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "frustration_score": frustration_score,
            "escalation_score": escalation_score,
            "urgency_score": urgency_score,
            "risk_score": risk_score,
            "sentiment_label": sentiment_label,
            "should_escalate": should_escalate,
            "escalation_reason": self._get_escalation_reason(
                frustration_score, escalation_score, urgency_score
            )
        }

    def _calculate_frustration_score(self, text: str) -> float:
        """Calculate frustration level based on keywords and patterns"""
        matches = sum(1 for keyword in self.FRUSTRATION_KEYWORDS if keyword in text)

        # Check for ALL CAPS (shouting)
        words = text.split()
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 1) / max(len(words), 1)

        # Check for repeated punctuation (!!! or ???)
        exclamation_count = text.count("!")
        question_count = text.count("?")
        repetition_score = min(1.0, (exclamation_count + question_count) / 10)

        return min(1.0, (matches * 0.3) + (caps_ratio * 0.3) + (repetition_score * 0.4))

    def _calculate_escalation_score(self, text: str) -> float:
        """Calculate likelihood patient wants to escalate"""
        matches = sum(1 for trigger in self.ESCALATION_TRIGGERS if trigger in text)
        return min(1.0, matches * 0.4)

    def _calculate_urgency_score(self, text: str) -> float:
        """Calculate urgency level"""
        urgency_words = [
            "emergency", "urgent", "asap", "immediately", "right now",
            "critical", "severe", "worst pain", "can't breathe", "chest pain",
            "bleeding", "fainted", "unconscious", "allergic reaction"
        ]
        matches = sum(1 for word in urgency_words if word in text)
        return min(1.0, matches * 0.5)

    def _get_escalation_reason(self, frustration: float, escalation: float, urgency: float) -> str:
        """Determine why escalation is recommended"""
        if urgency > 0.5:
            return "medical_urgency"
        if escalation > 0.5:
            return "requested_human"
        if frustration > 0.5:
            return "patient_frustration"
        return "risk_threshold"

    def get_response_suggestion(self, analysis: Dict) -> str:
        """Generate appropriate response based on sentiment"""
        if analysis["urgency_score"] > 0.5:
            return (
                "I understand this sounds urgent. For medical emergencies, "
                "please call 911 immediately. For urgent medical concerns, "
                "I can connect you with our nursing staff right away."
            )

        if analysis["should_escalate"]:
            if analysis["escalation_reason"] == "requested_human":
                return (
                    "I understand you'd like to speak with someone. "
                    "Let me connect you with our front desk staff who can "
                    "better assist you. One moment please."
                )
            elif analysis["escalation_reason"] == "patient_frustration":
                return (
                    "I apologize for any frustration. Your experience is "
                    "important to us. Let me connect you with a team member "
                    "who can provide personalized assistance."
                )

        if analysis["sentiment_label"] == "negative":
            return (
                "I understand your concern, and I want to make sure we "
                "address it properly. Could you tell me more about what's "
                "troubling you? I'm here to help."
            )

        if analysis["sentiment_label"] == "positive":
            return None  # No special response needed

        return None  # Neutral - no intervention needed
