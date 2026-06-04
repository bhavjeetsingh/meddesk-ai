"""
CareFirst Medical Center - Symptom Checker Engine
Guided triage flow to help patients before booking
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum


class UrgencyLevel(str, Enum):
    EMERGENCY = "emergency"      # Call 108 immediately
    URGENT = "urgent"           # See doctor today
    SOON = "soon"               # Book within 1-3 days
    ROUTINE = "routine"         # Book within a week
    SELF_CARE = "self_care"     # Home remedies, monitor


SYMPTOM_TREE = {
    "chest_pain": {
        "label": "Chest Pain / Discomfort",
        "category": "cardiac",
        "urgency": UrgencyLevel.EMERGENCY,
        "follow_up": [
            {"question": "Is the pain spreading to your arm, jaw, or back?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.URGENT},
            {"question": "Are you sweating profusely or feeling breathless?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.URGENT},
        ],
        "doctor": "cardiology",
        "message": "🚨 Chest pain can be a sign of a heart attack. Call 108 immediately or go to the nearest emergency room.",
        "self_care": None,
    },
    "breathlessness": {
        "label": "Difficulty Breathing / Breathlessness",
        "category": "respiratory",
        "urgency": UrgencyLevel.URGENT,
        "follow_up": [
            {"question": "Did this come on suddenly?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.URGENT},
            {"question": "Do you have asthma or COPD?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.URGENT},
        ],
        "doctor": "general",
        "message": "Breathlessness needs medical attention. Please see a doctor today.",
        "self_care": None,
    },
    "fever": {
        "label": "Fever",
        "category": "general",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "How high is the fever? (above 103°F / 39.4°C)", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Is it accompanied by severe headache or stiff neck?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Any rash on the body?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Has it lasted more than 3 days?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.SELF_CARE},
        ],
        "doctor": "general",
        "message": "Monitor your temperature. Stay hydrated.",
        "self_care": "Paracetamol 500mg every 6-8 hours as needed. Drink plenty of fluids. Rest. If fever persists >3 days or exceeds 103°F, see a doctor.",
    },
    "headache": {
        "label": "Headache",
        "category": "neurological",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Is it the worst headache of your life?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Any vision changes or vomiting?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Does it happen frequently? (more than 2x/week)", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.SELF_CARE},
        ],
        "doctor": "general",
        "message": "Most headaches are not serious, but frequent ones need evaluation.",
        "self_care": "Rest in a dark, quiet room. Apply peppermint oil on temples. Drink water. Paracetamol if needed. Avoid screen time.",
    },
    "stomach_pain": {
        "label": "Stomach / Abdominal Pain",
        "category": "gastro",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Is the pain severe and sudden?", "yes_urgency": UrgencyLevel.URGENT, "no_urgance": UrgencyLevel.ROUTINE},
            {"question": "Any blood in stool or vomit?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Any fever with it?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.SELF_CARE},
        ],
        "doctor": "general",
        "message": "Stomach pain can have many causes. Monitor and see a doctor if it worsens.",
        "self_care": "Drink warm water. Avoid spicy and oily food. BRAT diet (bananas, rice, applesauce, toast). ORS for loose motions.",
    },
    "diarrhea": {
        "label": "Loose Motions / Diarrhea",
        "category": "gastro",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Is there blood in the stool?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Unable to keep fluids down for 12+ hours?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.SELF_CARE},
            {"question": "Signs of dehydration (dry mouth, no urine)?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.SELF_CARE},
        ],
        "doctor": "general",
        "message": "Stay hydrated. Most cases resolve in 1-2 days.",
        "self_care": "ORS (Oral Rehydration Salts) after every loose motion. Drink 2-3 litres water. Avoid milk, spicy food, and street food. Curd rice is good.",
    },
    "cough": {
        "label": "Cough",
        "category": "respiratory",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Coughing blood?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Lasting more than 2 weeks?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.SELF_CARE},
            {"question": "Any weight loss or night sweats?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.SOON},
        ],
        "doctor": "general",
        "message": "Most coughs are viral. See a doctor if it persists.",
        "self_care": "Honey + ginger tea. Steam inhalation. Avoid cold water. Turmeric milk (haldi doodh) at night. Cough lozenges.",
    },
    "joint_pain": {
        "label": "Joint Pain / Body Ache",
        "category": "musculoskeletal",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Is the joint swollen, red, and hot?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Did it happen after an injury?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.ROUTINE},
        ],
        "doctor": "general",
        "message": "Joint pain can be from arthritis, strain, or injury.",
        "self_care": "Hot water fomentation. Gentle stretching. Avoid heavy lifting. Apply Diclofenac gel. If persistent, get X-ray done.",
    },
    "skin_rash": {
        "label": "Skin Rash / Itching",
        "category": "dermatological",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Is it spreading rapidly?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Any swelling of face or difficulty breathing?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.ROUTINE},
        ],
        "doctor": "general",
        "message": "Most rashes are allergic or infectious. See a doctor if spreading.",
        "self_care": "Apply calamine lotion. Avoid scratching. Wear cotton clothes. Antihistamine (Cetirizine) if itching.",
    },
    "eye_problem": {
        "label": "Eye Pain / Redness / Vision Issue",
        "category": "ophthalmological",
        "urgency": UrgencyLevel.SOON,
        "follow_up": [
            {"question": "Sudden vision loss?", "yes_urgency": UrgencyLevel.EMERGENCY, "no_urgency": UrgencyLevel.SOON},
            {"question": "Any injury to the eye?", "yes_urgency": UrgencyLevel.URGENT, "no_urgency": UrgencyLevel.SOON},
        ],
        "doctor": "general",
        "message": "Eye problems should be evaluated promptly to prevent complications.",
        "self_care": "Rest eyes. 20-20-20 rule: every 20 min, look at something 20 feet away for 20 seconds. Avoid rubbing.",
    },
    "ear_pain": {
        "label": "Ear Pain / Hearing Issue",
        "category": "ent",
        "urgency": UrgencyLevel.ROUTINE,
        "follow_up": [
            {"question": "Any discharge from ear?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.ROUTINE},
            {"question": "Severe pain with fever?", "yes_urgency": UrgencyLevel.SOON, "no_urgency": UrgencyLevel.ROUTINE},
        ],
        "doctor": "general",
        "message": "Ear infections are common and treatable.",
        "self_care": "Warm compress on ear. Don't put anything in the ear. Paracetamol for pain. See doctor if pain worsens.",
    },
}


def get_all_symptoms() -> List[Dict]:
    """Get list of all symptom options"""
    return [
        {"id": key, "label": val["label"], "urgency": val["urgency"]}
        for key, val in SYMPTOM_TREE.items()
    ]


def get_symptom(symptom_id: str) -> Optional[Dict]:
    """Get symptom details"""
    return SYMPTOM_TREE.get(symptom_id)


def evaluate_symptom(symptom_id: str, answers: List[bool]) -> Dict:
    """Evaluate symptom based on follow-up answers"""
    symptom = SYMPTOM_TREE.get(symptom_id)
    if not symptom:
        return {"error": "Unknown symptom"}

    urgency = symptom["urgency"]
    follow_ups = symptom.get("follow_up", [])

    for i, answer in enumerate(answers):
        if i < len(follow_ups):
            if answer:
                urgency = follow_ups[i]["yes_urgency"]
            else:
                urgency = follow_ups[i].get("no_urgency", urgency)

    urgency_messages = {
        UrgencyLevel.EMERGENCY: "🚨 EMERGENCY - Call 108 immediately or go to ER",
        UrgencyLevel.URGENT: "⚠️ URGENT - See a doctor TODAY",
        UrgencyLevel.SOON: "📋 SOON - Book an appointment within 1-3 days",
        UrgencyLevel.ROUTINE: "📅 ROUTINE - Book within a week",
        UrgencyLevel.SELF_CARE: "🏠 SELF CARE - Try home remedies, monitor",
    }

    return {
        "symptom": symptom["label"],
        "urgency": urgency,
        "urgency_message": urgency_messages.get(urgency, "Please see a doctor"),
        "doctor_recommended": symptom.get("doctor", "general"),
        "message": symptom.get("message", ""),
        "self_care": symptom.get("self_care"),
        "num_questions": len(follow_ups),
    }
