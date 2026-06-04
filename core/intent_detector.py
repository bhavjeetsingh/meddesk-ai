"""
CareFirst Medical Center - Intent Detection & Conversation Router
Classifies user intent and routes to appropriate handlers (Ollama)
"""
from typing import Dict, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger
import json
import re


class IntentDetector:
    """Detects user intent from messages"""

    INTENTS = {
        "appointment_booking": "User wants to schedule/book an appointment",
        "appointment_cancellation": "User wants to cancel an existing appointment",
        "appointment_reschedule": "User wants to change/reschedule an appointment",
        "appointment_inquiry": "User asks about existing appointments or availability",
        "doctor_lookup": "User is looking for a specific doctor or specialist",
        "service_inquiry": "User asks about services offered",
        "insurance_question": "User asks about insurance coverage or accepted providers",
        "billing_question": "User asks about costs, payment, or billing",
        "clinic_info": "User asks about clinic hours, location, contact, or general info",
        "directions": "User needs directions or parking information",
        "policy_question": "User asks about clinic policies (cancellation, no-show, etc.)",
        "emergency": "User mentions emergency, urgent, or severe symptoms",
        "prescription": "User asks about prescription refills or medications",
        "lab_results": "User asks about lab results or testing",
        "telehealth": "User asks about virtual/telehealth appointments",
        "complaint": "User is expressing dissatisfaction or making a complaint",
        "greeting": "User is greeting or starting a conversation",
        "farewell": "User is ending the conversation",
        "thanks": "User is expressing gratitude",
        "general_question": "General question not fitting other categories"
    }

    def __init__(self, config):
        self.config = config
        self.llm = ChatOllama(
            model=config.ollama_model,
            base_url=config.ollama_base_url,
            temperature=0
        )

    async def detect_intent(self, message: str, chat_history: list = None) -> Dict:
        """Detect the primary intent of a user message"""
        # Quick pattern matching for common intents
        quick_intent = self._quick_match(message)
        if quick_intent:
            return quick_intent

        # LLM-based intent detection
        history_context = ""
        if chat_history:
            recent = chat_history[-4:]
            history_context = "\n".join([
                f"{'User' if i % 2 == 0 else 'Assistant'}: {msg.content if hasattr(msg, 'content') else msg}"
                for i, msg in enumerate(recent)
            ])

        prompt = ChatPromptTemplate.from_template(
            """You are an intent classifier for a medical clinic receptionist AI.

Analyze the user message and classify it into one of these intents:
{intents}

Conversation History:
{history}

User Message: {message}

Respond with ONLY a JSON object in this exact format:
{{"intent": "intent_name", "confidence": 0.95, "entities": {{"doctor_name": null, "specialty": null, "date": null, "time": null, "service": null, "insurance": null}}}}"""
        )

        intents_text = "\n".join([f"- {k}: {v}" for k, v in self.INTENTS.items()])
        chain = prompt | self.llm | StrOutputParser()

        try:
            result = await chain.ainvoke({
                "intents": intents_text,
                "history": history_context or "No previous conversation",
                "message": message
            })

            # Parse JSON response
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]

            parsed = json.loads(result)
            return {
                "intent": parsed.get("intent", "general_question"),
                "confidence": parsed.get("confidence", 0.5),
                "entities": parsed.get("entities", {})
            }

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Intent detection failed: {e}, using fallback")
            return {
                "intent": "general_question",
                "confidence": 0.3,
                "entities": {}
            }

    def _quick_match(self, message: str) -> Optional[Dict]:
        """Quick pattern matching for obvious intents"""
        msg_lower = message.lower().strip()

        # Greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "namaste"]
        if any(g in msg_lower for g in greetings) and len(msg_lower.split()) <= 4:
            return {"intent": "greeting", "confidence": 0.95, "entities": {}}

        # Farewells
        farewells = ["bye", "goodbye", "see you", "take care", "have a good day", "alvida"]
        if any(f in msg_lower for f in farewells):
            return {"intent": "farewell", "confidence": 0.95, "entities": {}}

        # Thanks
        thanks = ["thank", "thanks", "appreciate", "helpful", "dhanyavaad", "shukriya"]
        if any(t in msg_lower for t in thanks) and len(msg_lower.split()) <= 5:
            return {"intent": "thanks", "confidence": 0.95, "entities": {}}

        # Emergency
        emergency_words = ["emergency", "911", "108", "102", "chest pain", "can't breathe", "severe", "urgent", "ambulance"]
        if any(e in msg_lower for e in emergency_words):
            return {"intent": "emergency", "confidence": 0.99, "entities": {}}

        # Appointment booking patterns
        booking_patterns = [
            r"book.*appointment", r"schedule.*appointment", r"make.*appointment",
            r"want.*see.*doctor", r"need.*appointment", r"set up.*appointment",
            r"appointment.*chahiye", r"appointment.*book"
        ]
        if any(re.search(p, msg_lower) for p in booking_patterns):
            return {"intent": "appointment_booking", "confidence": 0.9, "entities": {}}

        # Cancellation patterns
        cancel_patterns = [
            r"cancel.*appointment", r"cancel.*visit", r"cancel.*consultation"
        ]
        if any(re.search(p, msg_lower) for p in cancel_patterns):
            return {"intent": "appointment_cancellation", "confidence": 0.9, "entities": {}}

        # Reschedule patterns
        reschedule_patterns = [
            r"reschedule", r"change.*appointment", r"move.*appointment",
            r"switch.*time", r"different.*time"
        ]
        if any(re.search(p, msg_lower) for p in reschedule_patterns):
            return {"intent": "appointment_reschedule", "confidence": 0.9, "entities": {}}

        # Doctor lookup
        doctor_patterns = [
            r"dr\.?\s+\w+", r"doctor\s+\w+", r"find.*doctor",
            r"looking.*for.*doctor", r"who.*is.*dr"
        ]
        if any(re.search(p, msg_lower) for p in doctor_patterns):
            return {"intent": "doctor_lookup", "confidence": 0.85, "entities": {}}

        # Insurance
        insurance_patterns = [
            r"insurance", r"accept.*insurance", r"covered",
            r"do you take", r"in network", r"cashless"
        ]
        if any(re.search(p, msg_lower) for p in insurance_patterns):
            return {"intent": "insurance_question", "confidence": 0.85, "entities": {}}

        # Directions
        direction_patterns = [
            r"where.*located", r"directions", r"how.*get.*there",
            r"address", r"parking", r"map"
        ]
        if any(re.search(p, msg_lower) for p in direction_patterns):
            return {"intent": "directions", "confidence": 0.85, "entities": {}}

        # Hours
        hours_patterns = [
            r"hours", r"when.*open", r"when.*close", r"business hours", r"timing"
        ]
        if any(re.search(p, msg_lower) for p in hours_patterns):
            return {"intent": "clinic_info", "confidence": 0.85, "entities": {}}

        return None
