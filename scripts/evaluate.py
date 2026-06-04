"""
CareFirst Medical Center - Evaluation Script
Tests the system with sample queries (Ollama)
"""
import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from core.rag_engine import CareFirstRAG
from core.intent_detector import IntentDetector
from core.sentiment import SentimentAnalyzer
from loguru import logger


TEST_QUERIES = [
    # Greetings
    {"query": "Hello!", "expected_intent": "greeting"},
    {"query": "Namaste", "expected_intent": "greeting"},
    {"query": "Good morning", "expected_intent": "greeting"},

    # Appointment booking
    {"query": "I want to book an appointment", "expected_intent": "appointment_booking"},
    {"query": "Can I schedule a visit with Dr. Sharma?", "expected_intent": "appointment_booking"},
    {"query": "I need to see a cardiologist", "expected_intent": "doctor_lookup"},

    # Doctor lookup
    {"query": "Who is Dr. Mehta?", "expected_intent": "doctor_lookup"},
    {"query": "Tell me about Dr. Priya Sharma", "expected_intent": "doctor_lookup"},

    # Insurance
    {"query": "Do you accept Star Health insurance?", "expected_intent": "insurance_question"},
    {"query": "What insurance do you take?", "expected_intent": "insurance_question"},
    {"query": "Is cashless available?", "expected_intent": "insurance_question"},

    # Clinic info
    {"query": "What are your hours?", "expected_intent": "clinic_info"},
    {"query": "Where are you located?", "expected_intent": "directions"},

    # Services
    {"query": "What services do you offer?", "expected_intent": "service_inquiry"},
    {"query": "How much does a consultation cost?", "expected_intent": "billing_question"},

    # Billing
    {"query": "What are the fees?", "expected_intent": "billing_question"},
    {"query": "Do you accept UPI?", "expected_intent": "billing_question"},

    # Emergency
    {"query": "This is an emergency", "expected_intent": "emergency"},
    {"query": "I need an ambulance", "expected_intent": "emergency"},

    # Sentiment
    {"query": "I'm so frustrated with your service!", "expected_sentiment": "negative"},
    {"query": "This is the worst experience ever!", "expected_sentiment": "negative"},
    {"query": "Thank you so much, you've been very helpful!", "expected_sentiment": "positive"},
]


async def run_evaluation():
    """Run evaluation tests"""
    settings = get_settings()
    rag = CareFirstRAG(settings)
    intent_detector = IntentDetector(settings)
    sentiment_analyzer = SentimentAnalyzer()

    await rag.initialize()

    results = []
    correct_intent = 0
    total_intent = 0

    logger.info("=" * 60)
    logger.info("CareFirst Medical Center - Evaluation Run")
    logger.info("=" * 60)

    for test in TEST_QUERIES:
        query = test["query"]

        # Intent detection
        intent_result = await intent_detector.detect_intent(query)
        detected_intent = intent_result["intent"]

        # Sentiment analysis
        sentiment = sentiment_analyzer.analyze(query)

        # RAG response
        rag_result = await rag.query(query)

        # Check results
        intent_correct = True
        if "expected_intent" in test:
            total_intent += 1
            if detected_intent == test["expected_intent"]:
                correct_intent += 1
                intent_correct = True
            else:
                intent_correct = False

        sentiment_correct = True
        if "expected_sentiment" in test:
            if sentiment["sentiment_label"] != test["expected_sentiment"]:
                sentiment_correct = False

        result = {
            "query": query,
            "detected_intent": detected_intent,
            "expected_intent": test.get("expected_intent", "N/A"),
            "intent_correct": intent_correct,
            "sentiment": sentiment["sentiment_label"],
            "expected_sentiment": test.get("expected_sentiment", "N/A"),
            "sentiment_correct": sentiment_correct,
            "response_preview": rag_result["answer"][:100] + "..."
        }
        results.append(result)

        status = "PASS" if intent_correct and sentiment_correct else "FAIL"
        logger.info(f"[{status}] Query: {query}")
        logger.info(f"   Intent: {detected_intent} (expected: {test.get('expected_intent', 'N/A')})")
        logger.info(f"   Sentiment: {sentiment['sentiment_label']} (expected: {test.get('expected_sentiment', 'N/A')})")
        logger.info("")

    # Summary
    logger.info("=" * 60)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total queries tested: {len(TEST_QUERIES)}")
    if total_intent > 0:
        logger.info(f"Intent accuracy: {correct_intent}/{total_intent} ({correct_intent/total_intent*100:.1f}%)")
    logger.info("=" * 60)

    # Save results
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to evaluation_results.json")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
