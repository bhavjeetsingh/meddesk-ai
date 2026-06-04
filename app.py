"""
CareFirst Medical Center - Modern Chatbot-First UI
Chatbot is primary interface with interactive card options.
Sidebar has card tiles as alternative access.
"""
import chainlit as cl
from config import get_settings
from core.rag_engine import CareFirstRAG
from core.intent_detector import IntentDetector
from core.sentiment import SentimentAnalyzer
from core.database import init_db, seed_data
from core.health_tips import get_daily_tips, get_seasonal_tip, get_all_categories, get_tips_by_category
from core.symptom_checker import get_all_symptoms, get_symptom, evaluate_symptom, UrgencyLevel
from core.analytics import log_session, get_dashboard_stats, get_sentiment_distribution
from tools.appointments import AppointmentSystem
from tools.clinic_tools import ClinicTools
from tools.prescription_pdf import generate_prescription
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from loguru import logger
import json
import time
import re
import os

settings = get_settings()
rag_engine = CareFirstRAG(settings)
intent_detector = IntentDetector(settings)
sentiment_analyzer = SentimentAnalyzer(settings.escalation_threshold)
appointment_system = AppointmentSystem(settings)
clinic_tools = ClinicTools(settings)


# ══════════════════════════════════════════════════════════════
# CARD GRID ACTIONS (Main navigation in chat)
# ══════════════════════════════════════════════════════════════

def card_grid():
    """Main card grid for chatbot navigation"""
    return [
        cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
        cl.Action(name="card_symptoms", label="🔍 Check Symptoms", payload={"card": "symptoms"}),
        cl.Action(name="card_services", label="💊 View Services", payload={"card": "services"}),
        cl.Action(name="card_doctors", label="👨‍⚕️ Meet Doctors", payload={"card": "doctors"}),
        cl.Action(name="card_tips", label="💡 Health Tips", payload={"card": "tips"}),
        cl.Action(name="card_insurance", label="🛡️ Insurance Info", payload={"card": "insurance"}),
        cl.Action(name="card_emergency", label="🚨 Emergency", payload={"card": "emergency"}),
        cl.Action(name="card_profile", label="👤 My Profile", payload={"card": "profile"}),
        cl.Action(name="card_stats", label="📊 Analytics", payload={"card": "stats"}),
    ]


def back_button():
    """Back to main menu button"""
    return [cl.Action(name="card_back", label="← Back to Menu", payload={"card": "home"})]


def sidebar_toggle():
    """Sidebar toggle button"""
    return [cl.Action(name="toggle_sidebar", label="📋 Open Sidebar", payload={"action": "sidebar"})]


def doctor_cards():
    """Doctor selection cards for booking"""
    return [
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Priya Sharma - General ₹1,000", payload={"doctor": "priya"}),
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Rajesh Mehta - Cardiology ₹1,500", payload={"doctor": "rajesh"}),
        cl.Action(name="select_doctor", label="👩‍⚕️ Dr. Anita Desai - Dermatology ₹1,200", payload={"doctor": "anita"}),
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Vikram Patel - Orthopedics ₹1,500", payload={"doctor": "vikram"}),
        cl.Action(name="select_doctor", label="👩‍⚕️ Dr. Sunita Reddy - Pediatrics ₹1,000", payload={"doctor": "sunita"}),
    ] + back_button()


def symptom_cards():
    """Symptom selection cards"""
    return [
        cl.Action(name="select_symptom", label="🤒 Fever", payload={"symptom": "fever"}),
        cl.Action(name="select_symptom", label="🤕 Headache", payload={"symptom": "headache"}),
        cl.Action(name="select_symptom", label="💔 Chest Pain", payload={"symptom": "chest_pain"}),
        cl.Action(name="select_symptom", label="🤢 Stomach Pain", payload={"symptom": "stomach_pain"}),
        cl.Action(name="select_symptom", label="🩹 Skin Rash", payload={"symptom": "skin_rash"}),
        cl.Action(name="select_symptom", label="😰 Anxiety", payload={"symptom": "anxiety"}),
        cl.Action(name="select_symptom", label="😴 Insomnia", payload={"symptom": "insomnia"}),
        cl.Action(name="select_symptom", label="🤧 Cold/Cough", payload={"symptom": "cold_cough"}),
    ] + back_button()


def service_cards():
    """Service category cards"""
    return [
        cl.Action(name="select_service", label="🩺 Consultation", payload={"service": "consultation"}),
        cl.Action(name="select_service", label="🔬 Diagnostic Tests", payload={"service": "tests"}),
        cl.Action(name="select_service", label="💉 Procedures", payload={"service": "procedures"}),
        cl.Action(name="select_service", label="🏥 Full Health Checkup", payload={"service": "checkup"}),
        cl.Action(name="select_service", label="📱 Teleconsultation", payload={"service": "tele"}),
    ] + back_button()


def specialty_cards():
    """Doctor specialty selection cards"""
    return [
        cl.Action(name="filter_doctors", label="🩺 General Practice", payload={"specialty": "General"}),
        cl.Action(name="filter_doctors", label="❤️ Cardiology", payload={"specialty": "Cardiology"}),
        cl.Action(name="filter_doctors", label="🧴 Dermatology", payload={"specialty": "Dermatology"}),
        cl.Action(name="filter_doctors", label="🦴 Orthopedics", payload={"specialty": "Orthopedics"}),
        cl.Action(name="filter_doctors", label="👶 Pediatrics", payload={"specialty": "Pediatrics"}),
    ] + back_button()


def tip_cards():
    """Health tip type cards"""
    return [
        cl.Action(name="select_tip", label="☀️ Daily Tips", payload={"tip": "daily"}),
        cl.Action(name="select_tip", label="🌡️ Seasonal Tips", payload={"tip": "seasonal"}),
        cl.Action(name="select_tip", label="📚 By Category", payload={"tip": "category"}),
    ] + back_button()


def insurance_cards():
    """Insurance info cards"""
    return [
        cl.Action(name="select_insurance", label="💳 Cashless Providers", payload={"insurance": "cashless"}),
        cl.Action(name="select_insurance", label="🇮🇳 Government Schemes", payload={"insurance": "government"}),
        cl.Action(name="select_insurance", label="📱 Payment Methods", payload={"insurance": "payment"}),
    ] + back_button()


def profile_cards():
    """Profile action cards"""
    return [
        cl.Action(name="profile_action", label="👁️ View Profile", payload={"action": "view"}),
        cl.Action(name="profile_action", label="✏️ Update Profile", payload={"action": "update"}),
        cl.Action(name="profile_action", label="📋 My History", payload={"action": "history"}),
        cl.Action(name="profile_action", label="📄 Download Prescription", payload={"action": "prescription"}),
    ] + back_button()


# ══════════════════════════════════════════════════════════════
# SIDEBAR DASHBOARD BUILDERS
# ══════════════════════════════════════════════════════════════

def build_home_sidebar():
    return [
        cl.Text(content=f"""## 🏥 {settings.clinic_name}

**Hours:** {settings.clinic_hours}
**Phone:** {settings.clinic_phone}
**Address:** {settings.clinic_address}

---

### Quick Actions
Click the cards in the chat or type:
- `book appointment` — Schedule a visit
- `doctors` — Meet our specialists  
- `insurance` — Check your coverage
- `services` — View all services
- `emergency` — Urgent help""", name="home_dashboard")
    ]


def build_doctors_sidebar():
    return [
        cl.Text(content="""## 👨‍⚕️ Our Doctors

### Dr. Priya Sharma
- **Specialty:** General Practice
- **Qualification:** MBBS, MD (Medicine)
- **Experience:** 10+ years
- **Fee:** ₹1,000
- **Available:** Mon-Sat

### Dr. Rajesh Mehta
- **Specialty:** Cardiology
- **Qualification:** MBBS, MD (Cardiology), DM
- **Experience:** 15+ years
- **Fee:** ₹1,500
- **Available:** Mon, Wed, Fri, Sat

### Dr. Anita Desai
- **Specialty:** Dermatology
- **Qualification:** MBBS, MD (Dermatology)
- **Experience:** 8+ years
- **Fee:** ₹1,200
- **Available:** Mon-Fri

### Dr. Vikram Patel
- **Specialty:** Orthopedics
- **Qualification:** MBBS, MS (Orthopedics)
- **Experience:** 12+ years
- **Fee:** ₹1,500
- **Available:** Mon-Sat

### Dr. Sunita Reddy
- **Specialty:** Pediatrics
- **Qualification:** MBBS, MD (Pediatrics)
- **Experience:** 7+ years
- **Fee:** ₹1,000
- **Available:** Mon-Sat

---

Click **Book Appointment** in the chat to schedule.""", name="doctors_dashboard")
    ]


def build_symptom_sidebar():
    symptoms = get_all_symptoms()
    items = "\n".join([f"- {s['label']}" for s in symptoms])
    return [
        cl.Text(content=f"""## 🩺 Symptom Checker

Click a symptom card in the chat to check urgency.

**Available Symptoms:**
{items}

---

**⚠️ For emergencies, call 108 immediately.**""", name="symptom_dashboard")
    ]


def build_tips_sidebar():
    tips = get_daily_tips(3)
    seasonal = get_seasonal_tip()
    tip_text = "\n\n".join([f"**{t['title']}**\n{t['tip']}" for t in tips])
    return [
        cl.Text(content=f"""## 💡 Daily Health Tips

{tip_text}

---

### 🌡️ Seasonal Tip
**{seasonal['title']}**
{seasonal['tip']}""", name="tips_dashboard")
    ]


def build_profile_sidebar(patient, msg_count, duration):
    name = patient.get("name", "Not registered")
    phone = patient.get("phone", "Not set")
    return [
        cl.Text(content=f"""## 👤 My Profile

| Field | Value |
|-------|-------|
| Name | {name} |
| Phone | {phone} |
| Messages | {msg_count} |
| Duration | {duration // 60}m {duration % 60}s |

---

**Actions:**
- Click **My History** to view past chats
- Click **Download Prescription** for Rx PDF
- Click **Update Profile** to change info""", name="profile_dashboard")
    ]


def build_analytics_sidebar():
    stats = get_dashboard_stats()
    sentiment = get_sentiment_distribution()

    trend = ""
    for day in stats.get("daily_trend", []):
        bar = "█" * min(day["sessions"], 10)
        trend += f"| {day['label']} | {bar} {day['sessions']} |\n"

    return [
        cl.Text(content=f"""## 📊 Analytics Dashboard

### Overall Stats
| Metric | Value |
|--------|-------|
| Total Sessions | {stats['total_sessions']} |
| Total Messages | {stats['total_messages']} |
| Sessions Today | {stats['sessions_today']} |
| Avg Duration | {stats['avg_session_duration']}s |
| Sentiment | {stats['sentiment_label']} |

### Sentiment
| Type | % |
|------|---|
| 😊 Positive | {sentiment['positive_pct']}% |
| 😐 Neutral | {sentiment['neutral_pct']}% |
| 😟 Concerned | {sentiment['concerned_pct']}% |

### Weekly Trend
| Day | Sessions |
|-----|----------|
{trend if trend else "| --- | No data |"}

### Top Intentions
{chr(10).join([f"- {i['intent'].replace('_',' ').title()}: {i['count']}" for i in stats.get('top_intents',[])[:5]]) or "- No data yet"}""", name="analytics_dashboard")
    ]


def build_insurance_sidebar():
    return [
        cl.Text(content="""## 🏥 Insurance & Payment

### Cashless Providers
- ⭐ Star Health & Allied Insurance
- 🏦 ICICI Lombard
- 🛡️ Bajaj Allianz
- 🏢 HDFC ERGO
- 🆕 New India Assurance

### Government Schemes
- 🇮🇳 Ayushman Bharat (PMJAY) — up to ₹5L/year
- 🏛️ CGHS — Central Govt employees
- 🎖️ ECHS — Ex-servicemen
- 🌟 MJPJAY — Maharashtra scheme

### Payment Methods
- 💳 Credit/Debit Cards
- 📱 UPI (GPay, PhonePe, Paytm)
- 🏦 Net Banking
- 💵 Cash

**GST:** 18% on consultation fees""", name="insurance_dashboard")
    ]


def build_services_sidebar():
    return [
        cl.Text(content="""## 🩺 Services & Fees

| Service | Cost | Duration |
|---------|------|----------|
| General Consultation | ₹1,000 | 30 min |
| Cardiology | ₹1,500 | 45 min |
| Dermatology | ₹1,200 | 30 min |
| Orthopedics | ₹1,500 | 45 min |
| Pediatrics | ₹1,000 | 30 min |
| ECG | ₹500 | 15 min |
| Echocardiography | ₹3,000 | 30 min |
| Blood Tests | ₹300-2,000 | 15 min |
| Diabetes Management | ₹1,200 | 30 min |
| Vaccination | ₹100-2,500 | 15 min |
| Full Health Checkup | ₹3,500 | 2 hours |
| Teleconsultation | ₹800 | 20 min |

**GST:** 18% applicable on all services""", name="services_dashboard")
    ]


def build_emergency_sidebar():
    return [
        cl.Text(content="""## 🚨 EMERGENCY

### Call NOW
| Service | Number |
|---------|--------|
| 🚑 Ambulance | **108** |
| 🏥 Medical Emergency | **102** |
| ☠️ Poison Control | **1066** |
| 🩸 Blood Bank | +91 22 2496 6111 |

### Nearby Hospitals
- Breach Candy Hospital — 2 km
- Jaslok Hospital — 3 km
- Kokilaben Hospital — 5 km

### Clinic Urgent Line
📞 +91 98765 43210""", name="emergency_dashboard")
    ]


# ══════════════════════════════════════════════════════════════
# SIDEBAR UPDATER
# ══════════════════════════════════════════════════════════════

async def update_sidebar(dashboard_type: str):
    """Update sidebar with the selected dashboard"""
    await cl.ElementSidebar.set_title(dashboard_type.replace("_", " ").title())

    builders = {
        "home": build_home_sidebar,
        "doctors": build_doctors_sidebar,
        "symptoms": build_symptom_sidebar,
        "tips": build_tips_sidebar,
        "insurance": build_insurance_sidebar,
        "services": build_services_sidebar,
        "emergency": build_emergency_sidebar,
    }

    if dashboard_type == "profile":
        patient = cl.user_session.get("patient_info", {})
        msg_count = cl.user_session.get("message_count", 0)
        duration = int(time.time() - cl.user_session.get("session_start", time.time()))
        elements = build_profile_sidebar(patient, msg_count, duration)
    elif dashboard_type == "analytics":
        elements = build_analytics_sidebar()
    elif dashboard_type in builders:
        elements = builders[dashboard_type]()
    else:
        elements = build_home_sidebar()

    await cl.ElementSidebar.set_elements(elements)


# ══════════════════════════════════════════════════════════════
# CHAT START
# ══════════════════════════════════════════════════════════════

@cl.on_chat_start
async def on_chat_start():
    await init_db()
    await seed_data()
    await rag_engine.initialize()

    cl.user_session.set("conversation_history", [])
    cl.user_session.set("patient_info", {})
    cl.user_session.set("booking_state", None)
    cl.user_session.set("symptom_state", None)
    cl.user_session.set("session_start", time.time())
    cl.user_session.set("message_count", 0)
    cl.user_session.set("session_id", f"sess_{int(time.time())}")
    cl.user_session.set("intents_log", [])
    cl.user_session.set("sentiments_log", [])
    cl.user_session.set("current_flow", None)

    # Load home sidebar
    await update_sidebar("home")

    # Welcome message with card grid
    await cl.Message(
        content=f"## 🏥 Welcome to {settings.clinic_name}\n\n"
                f"I'm **CareFirst AI** — your virtual health assistant.\n\n"
                f"**Choose an option below or type your question:**\n\n"
                f"💡 **Tip:** Click the sidebar button in the header or use the card below to open the dashboard.",
        actions=card_grid() + sidebar_toggle() + sidebar_toggle()
    ).send()


# ══════════════════════════════════════════════════════════════
# CARD ACTION HANDLERS
# ══════════════════════════════════════════════════════════════

@cl.action_callback("card_home")
async def on_card_home(action):
    await update_sidebar("home")
    await cl.Message(
        content="## 🏥 Home\n\nChoose an option below:",
        actions=card_grid() + sidebar_toggle() + sidebar_toggle()
    ).send()


@cl.action_callback("card_back")
async def on_card_back(action):
    await update_sidebar("home")
    await cl.Message(
        content="## 🏥 Main Menu\n\nChoose an option below:",
        actions=card_grid() + sidebar_toggle() + sidebar_toggle()
    ).send()


@cl.action_callback("toggle_sidebar")
async def on_toggle_sidebar(action):
    """Toggle sidebar visibility"""
    # The sidebar toggle is handled by Chainlit's built-in mechanism
    # This action just refreshes the sidebar content
    await update_sidebar("home")
    await cl.Message(
        content="## 📋 Sidebar Opened\n\nDashboard details are now visible in the sidebar →",
        actions=card_grid() + sidebar_toggle()
    ).send()


@cl.action_callback("card_book")
async def on_card_book(action):
    await update_sidebar("doctors")
    cl.user_session.set("current_flow", "booking")
    await cl.Message(
        content="## 📅 Book Appointment\n\n**Step 1: Choose a doctor:**",
        actions=doctor_cards()
    ).send()


@cl.action_callback("select_doctor")
async def on_select_doctor(action):
    doctor = action.payload.get("doctor")
    doctor_map = {
        "priya": {"name": "Dr. Priya Sharma", "specialty": "General Practice", "fee": 1000, "id": 1},
        "rajesh": {"name": "Dr. Rajesh Mehta", "specialty": "Cardiology", "fee": 1500, "id": 2},
        "anita": {"name": "Dr. Anita Desai", "specialty": "Dermatology", "fee": 1200, "id": 3},
        "vikram": {"name": "Dr. Vikram Patel", "specialty": "Orthopedics", "fee": 1500, "id": 4},
        "sunita": {"name": "Dr. Sunita Reddy", "specialty": "Pediatrics", "fee": 1000, "id": 5},
    }
    selected = doctor_map.get(doctor, doctor_map["priya"])
    
    cl.user_session.set("booking_state", {
        "step": "date",
        "doctor": selected["name"],
        "doctor_id": selected["id"],
        "fee": selected["fee"],
        "specialty": selected["specialty"]
    })
    
    await cl.Message(
        content=f"## 📅 Book Appointment\n\n"
                f"**Doctor:** {selected['name']} ({selected['specialty']})\n"
                f"**Fee:** ₹{selected['fee']}\n\n"
                f"**Step 2: Choose a date:**",
        actions=[
            cl.Action(name="select_date", label="📅 Today", payload={"date": "today"}),
            cl.Action(name="select_date", label="📅 Tomorrow", payload={"date": "tomorrow"}),
            cl.Action(name="select_date", label="📅 This Week", payload={"date": "week"}),
        ] + back_button()
    ).send()


@cl.action_callback("select_date")
async def on_select_date(action):
    date_option = action.payload.get("date")
    booking = cl.user_session.get("booking_state", {})
    
    if date_option == "today":
        appt_date = date.today()
    elif date_option == "tomorrow":
        appt_date = date.today() + timedelta(days=1)
    else:
        appt_date = date.today() + timedelta(days=3)
    
    booking["date"] = appt_date
    booking["step"] = "confirm"
    cl.user_session.set("booking_state", booking)
    
    await cl.Message(
        content=f"## 📅 Book Appointment\n\n"
                f"**Doctor:** {booking['doctor']}\n"
                f"**Date:** {appt_date.strftime('%A, %B %d, %Y')}\n"
                f"**Fee:** ₹{booking['fee']} (+18% GST)\n\n"
                f"**Step 3: Confirm booking**\n\n"
                f"Please share your **name and phone number** to confirm.",
        actions=back_button() + sidebar_toggle()
    ).send()


@cl.action_callback("card_symptoms")
async def on_card_symptoms(action):
    await update_sidebar("symptoms")
    cl.user_session.set("current_flow", "symptoms")
    await cl.Message(
        content="## 🩺 Symptom Checker\n\n**Select your symptom:**",
        actions=symptom_cards()
    ).send()


@cl.action_callback("select_symptom")
async def on_select_symptom(action):
    symptom_id = action.payload.get("symptom")
    symptom = get_symptom(symptom_id)
    
    if not symptom:
        await cl.Message(content="Symptom not found. Please try again.")
        return
    
    follow_ups = symptom.get("follow_up", [])
    if follow_ups:
        cl.user_session.set("symptom_state", {
            "symptom_id": symptom_id,
            "current_q": 0,
            "answers": []
        })
        q = follow_ups[0]["question"]
        await cl.Message(
            content=f"## 🩺 {symptom.get('label', symptom_id)}\n\n"
                    f"**Q1:** {q}\n\n"
                    f"Type: `yes` or `no`",
            actions=back_button() + sidebar_toggle()
        ).send()
    else:
        result = evaluate_symptom(symptom_id, [])
        color = {"emergency": "🚨", "urgent": "⚠️", "soon": "📋", "routine": "📅", "self_care": "🏠"}.get(result.get("urgency", ""), "")
        msg = f"{color} **Result: {result.get('symptom', '')}**\n\n**Urgency:** {result.get('urgency_message', '')}\n**Doctor:** {result.get('doctor_recommended', 'General').title()}\n\n{result.get('message', '')}"
        if result.get("self_care"):
            msg += f"\n\n**Home Care:** {result['self_care']}"
        await cl.Message(content=msg, actions=card_grid() + sidebar_toggle()).send()


@cl.action_callback("card_services")
async def on_card_services(action):
    await update_sidebar("services")
    cl.user_session.set("current_flow", "services")
    await cl.Message(
        content="## 💊 Services & Fees\n\n**Choose a category:**",
        actions=service_cards()
    ).send()


@cl.action_callback("select_service")
async def on_select_service(action):
    service = action.payload.get("service")
    services_info = {
        "consultation": "## 🩺 Consultation Services\n\n| Service | Fee | Duration |\n|---------|-----|----------|\n| General Consultation | ₹1,000 | 30 min |\n| Cardiology | ₹1,500 | 45 min |\n| Dermatology | ₹1,200 | 30 min |\n| Orthopedics | ₹1,500 | 45 min |\n| Pediatrics | ₹1,000 | 30 min |",
        "tests": "## 🔬 Diagnostic Tests\n\n| Test | Cost | Duration |\n|------|------|----------|\n| Blood Tests | ₹300-2,000 | 15 min |\n| ECG | ₹500 | 15 min |\n| Echocardiography | ₹3,000 | 30 min |\n| X-Ray | ₹800 | 20 min |\n| Ultrasound | ₹1,500 | 30 min |",
        "procedures": "## 💉 Procedures\n\n| Procedure | Cost | Duration |\n|-----------|------|----------|\n| Vaccination | ₹100-2,500 | 15 min |\n| Diabetes Management | ₹1,200 | 30 min |\n| Minor Surgery | ₹2,000-5,000 | 1 hour |\n| Wound Care | ₹500 | 20 min |",
        "checkup": "## 🏥 Full Health Checkup\n\n**Package: ₹3,500**\n\nIncludes:\n- Complete Blood Count\n- Lipid Profile\n- Liver Function Test\n- Kidney Function Test\n- Thyroid Profile\n- ECG\n- Chest X-Ray\n- Doctor Consultation\n\n**Duration:** 2 hours",
        "tele": "## 📱 Teleconsultation\n\n**Fee: ₹800**\n\n- Video consultation with doctor\n- Duration: 20 minutes\n- Available: Mon-Sat, 9 AM - 8 PM\n- Prescription sent to your email\n- Follow-up within 7 days"
    }
    
    content = services_info.get(service, "Service information not available.")
    await cl.Message(
        content=content,
        actions=service_cards()
    ).send()


@cl.action_callback("card_doctors")
async def on_card_doctors(action):
    await update_sidebar("doctors")
    cl.user_session.set("current_flow", "doctors")
    await cl.Message(
        content="## 👨‍⚕️ Our Doctors\n\n**Choose a specialty:**",
        actions=specialty_cards()
    ).send()


@cl.action_callback("filter_doctors")
async def on_filter_doctors(action):
    specialty = action.payload.get("specialty")
    doctors_info = {
        "General": "## 🩺 General Practice\n\n### Dr. Priya Sharma\n- **Qualification:** MBBS, MD (Medicine)\n- **Experience:** 10+ years\n- **Fee:** ₹1,000\n- **Available:** Mon-Sat\n- **Specialties:** Preventive healthcare, Diabetes, Women's health",
        "Cardiology": "## ❤️ Cardiology\n\n### Dr. Rajesh Mehta\n- **Qualification:** MBBS, MD (Cardiology), DM\n- **Experience:** 15+ years\n- **Fee:** ₹1,500\n- **Available:** Mon, Wed, Fri, Sat\n- **Specialties:** Interventional cardiology, Heart failure, Preventive cardiology",
        "Dermatology": "## 🧴 Dermatology\n\n### Dr. Anita Desai\n- **Qualification:** MBBS, MD (Dermatology)\n- **Experience:** 8+ years\n- **Fee:** ₹1,200\n- **Available:** Mon-Fri\n- **Specialties:** Cosmetic dermatology, Acne treatment, Laser therapy",
        "Orthopedics": "## 🦴 Orthopedics\n\n### Dr. Vikram Patel\n- **Qualification:** MBBS, MS (Orthopedics)\n- **Experience:** 12+ years\n- **Fee:** ₹1,500\n- **Available:** Mon-Sat\n- **Specialties:** Joint replacement, Sports injuries, Spinal disorders",
        "Pediatrics": "## 👶 Pediatrics\n\n### Dr. Sunita Reddy\n- **Qualification:** MBBS, MD (Pediatrics)\n- **Experience:** 7+ years\n- **Fee:** ₹1,000\n- **Available:** Mon-Sat\n- **Specialties:** Newborn care, Vaccinations, Developmental pediatrics"
    }
    
    content = doctors_info.get(specialty, "Doctor information not available.")
    await cl.Message(
        content=content,
        actions=specialty_cards()
    ).send()


@cl.action_callback("card_tips")
async def on_card_tips(action):
    await update_sidebar("tips")
    cl.user_session.set("current_flow", "tips")
    await cl.Message(
        content="## 💡 Health Tips\n\n**Choose a type:**",
        actions=tip_cards()
    ).send()


@cl.action_callback("select_tip")
async def on_select_tip(action):
    tip_type = action.payload.get("tip")
    
    if tip_type == "daily":
        tips = get_daily_tips(3)
        tip_text = "\n\n".join([f"**{t['title']}**\n{t['tip']}" for t in tips])
        content = f"## ☀️ Daily Health Tips\n\n{tip_text}"
    elif tip_type == "seasonal":
        seasonal = get_seasonal_tip()
        content = f"## 🌡️ Seasonal Tip\n\n**{seasonal['title']}**\n{seasonal['tip']}"
    else:
        categories = get_all_categories()
        content = "## 📚 Tips by Category\n\n" + "\n".join([f"- {c}" for c in categories])
    
    await cl.Message(content=content, actions=tip_cards()).send()


@cl.action_callback("card_insurance")
async def on_card_insurance(action):
    await update_sidebar("insurance")
    cl.user_session.set("current_flow", "insurance")
    await cl.Message(
        content="## 🛡️ Insurance & Payment\n\n**Choose an option:**",
        actions=insurance_cards()
    ).send()


@cl.action_callback("select_insurance")
async def on_select_insurance(action):
    insurance_type = action.payload.get("insurance")
    
    if insurance_type == "cashless":
        content = "## 💳 Cashless Providers\n\n- ⭐ Star Health & Allied Insurance\n- 🏦 ICICI Lombard\n- 🛡️ Bajaj Allianz\n- 🏢 HDFC ERGO\n- 🆕 New India Assurance\n\n**Note:** Please carry your insurance card and photo ID."
    elif insurance_type == "government":
        content = "## 🇮🇳 Government Schemes\n\n- **Ayushman Bharat (PMJAY)** — up to ₹5L/year\n- **CGHS** — Central Govt employees\n- **ECHS** — Ex-servicemen\n- **MJPJAY** — Maharashtra scheme\n\n**Eligibility:** Check at reception with required documents."
    else:
        content = "## 📱 Payment Methods\n\n- 💳 Credit/Debit Cards\n- 📱 UPI (GPay, PhonePe, Paytm)\n- 🏦 Net Banking\n- 💵 Cash\n\n**GST:** 18% applicable on all services"
    
    await cl.Message(content=content, actions=insurance_cards()).send()


@cl.action_callback("card_emergency")
async def on_card_emergency(action):
    await update_sidebar("emergency")
    await cl.Message(
        content="## 🚨 EMERGENCY\n\n### Call NOW\n| Service | Number |\n|---------|--------|\n| 🚑 Ambulance | **108** |\n| 🏥 Medical Emergency | **102** |\n| ☠️ Poison Control | **1066** |\n| 🩸 Blood Bank | +91 22 2496 6111 |\n\n### Nearby Hospitals\n- Breach Candy Hospital — 2 km\n- Jaslok Hospital — 3 km\n- Kokilaben Hospital — 5 km\n\n### Clinic Urgent Line\n📞 +91 98765 43210",
        actions=back_button() + sidebar_toggle() + sidebar_toggle()
    ).send()


@cl.action_callback("card_profile")
async def on_card_profile(action):
    await update_sidebar("profile")
    cl.user_session.set("current_flow", "profile")
    await cl.Message(
        content="## 👤 My Profile\n\n**Choose an action:**",
        actions=profile_cards()
    ).send()


@cl.action_callback("profile_action")
async def on_profile_action(action):
    profile_action = action.payload.get("action")
    
    if profile_action == "view":
        patient = cl.user_session.get("patient_info", {})
        name = patient.get("name", "Not registered")
        phone = patient.get("phone", "Not set")
        content = f"## 👤 My Profile\n\n| Field | Value |\n|-------|-------|\n| Name | {name} |\n| Phone | {phone} |"
    elif profile_action == "update":
        cl.user_session.set("awaiting_profile_update", True)
        content = "## ✏️ Update Profile\n\nPlease provide: `Name, Phone, Age, Gender`\n\nExample: `John Doe, 9876543210, 30, M`"
    elif profile_action == "history":
        history = cl.user_session.get("conversation_history", [])
        history_text = "\n".join([f"{'🧑' if m['role']=='user' else '🤖'} {m['content'][:100]}" for m in history[-5:]])
        content = f"## 📋 Recent Chat History\n\n{history_text or 'No history yet.'}"
    else:
        content = "## 📄 Prescription\n\nTo generate a prescription, provide:\n`PatientName, Age, Gender, Diagnosis, Medicine Dose Frequency Duration`\n\nExample: `Amit Patel, 35, M, Viral Fever, Paracetamol 500mg 3x/day 5days`"
    
    await cl.Message(content=content, actions=profile_cards()).send()


@cl.action_callback("card_stats")
async def on_card_stats(action):
    await update_sidebar("analytics")
    stats = get_dashboard_stats()
    sentiment = get_sentiment_distribution()
    
    content = f"""## 📊 Analytics Dashboard

### Overall Stats
| Metric | Value |
|--------|-------|
| Total Sessions | {stats['total_sessions']} |
| Total Messages | {stats['total_messages']} |
| Sessions Today | {stats['sessions_today']} |
| Avg Duration | {stats['avg_session_duration']}s |

### Sentiment
| Type | % |
|------|---|
| 😊 Positive | {sentiment['positive_pct']}% |
| 😐 Neutral | {sentiment['neutral_pct']}% |
| 😟 Concerned | {sentiment['concerned_pct']}% |"""
    
    await cl.Message(content=content, actions=back_button() + sidebar_toggle() + sidebar_toggle()).send()


# ══════════════════════════════════════════════════════════════
# FREE-TEXT MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════

@cl.on_message
async def on_message(message: cl.Message):
    user_msg = message.content.strip()
    history = cl.user_session.get("conversation_history", [])
    count = cl.user_session.get("message_count", 0) + 1
    cl.user_session.set("message_count", count)

    session_id = cl.user_session.get("session_id", "unknown")
    intents_log = cl.user_session.get("intents_log", [])
    sentiments_log = cl.user_session.get("sentiments_log", [])

    lower = user_msg.lower().strip()

    # ─── Handle profile update ───
    if cl.user_session.get("awaiting_profile_update"):
        parts = [p.strip() for p in user_msg.split(",")]
        if len(parts) >= 2:
            patient_info = {"name": parts[0], "phone": parts[1], "age": parts[2] if len(parts) > 2 else "", "gender": parts[3] if len(parts) > 3 else ""}
            cl.user_session.set("patient_info", patient_info)
            cl.user_session.set("awaiting_profile_update", False)
            await cl.Message(
                content=f"✅ Profile updated!\n**Name:** {patient_info['name']} | **Phone:** {patient_info['phone']}",
                actions=profile_cards()
            )
            await update_sidebar("profile")
            return
        await cl.Message(content="Format: `Name, Phone, Age, Gender`")
        return

    # ─── Handle prescription generation ───
    if "prescription" in lower and ("generate" in lower or "download" in lower or "pdf" in lower):
        await cl.Message(content="📄 To generate a prescription, provide:\n`PatientName, Age, Gender, Diagnosis, Medicine Dose Frequency Duration`\n\nExample: `Amit Patel, 35, M, Viral Fever, Paracetamol 500mg 3x/day 5days`")
        return

    if ("," in user_msg and "mg" in user_msg.lower()) and not cl.user_session.get("booking_state"):
        try:
            parts = [p.strip() for p in user_msg.split(",")]
            pdf_path = generate_prescription(
                patient_name=parts[0], patient_age=parts[1] if len(parts) > 1 else "30",
                patient_gender=parts[2] if len(parts) > 2 else "M",
                diagnosis=parts[3] if len(parts) > 3 else "General checkup",
                doctor_name="Priya Sharma", doctor_qualification="MBBS, MD (Medicine)",
                registration_number="MCI/2015/12345",
                medications=[{"name": parts[4].split()[0] if len(parts) > 4 else "Paracetamol", "dosage": "500mg", "frequency": "3 times daily", "duration": "5 days"}],
                instructions="Take after food. Complete the full course.",
                follow_up="After 1 week if symptoms persist.",
            )
            await cl.Message(content=f"📄 **Prescription generated!**\n`{pdf_path}`")
            return
        except Exception as e:
            await cl.Message(content=f"Error: {str(e)}")
            return

    # ─── Handle booking confirmation ───
    booking_state = cl.user_session.get("booking_state", {})
    if booking_state and booking_state.get("step") == "confirm":
        phone_match = re.search(r'(\+91\s?\d{10}|\d{10})', user_msg)
        if phone_match or len(user_msg.split()) >= 2:
            doctor = booking_state.get("doctor", "Dr. Priya Sharma")
            fee = booking_state.get("fee", 1000)
            appt_date = booking_state.get("date", date.today() + timedelta(days=1))
            gst = int(fee * 0.18)
            await cl.Message(
                content=f"✅ **Appointment Confirmed!**\n\n| | |\n|---|---|\n| 👤 **Patient** | {user_msg.strip()} |\n| 👨‍⚕️ **Doctor** | {doctor} |\n| 📅 **Date** | {appt_date.strftime('%A, %B %d, %Y')} |\n| 💰 **Total** | ₹{fee + gst} (incl. GST) |\n\n📱 Confirmation SMS will be sent.",
                actions=card_grid() + sidebar_toggle()
            )
            cl.user_session.set("booking_state", None)
            return
        await cl.Message(content="Please share your **name and phone number** to confirm.")
        return

    # ─── Handle symptom follow-up ───
    if cl.user_session.get("symptom_state"):
        state = cl.user_session.get("symptom_state")
        answer = lower in ["yes", "y", "haan", "ha", "true", "1"]
        state["answers"].append(answer)
        state["current_q"] += 1
        symptom = get_symptom(state["symptom_id"])
        follow_ups = symptom.get("follow_up", [])
        if state["current_q"] >= len(follow_ups):
            result = evaluate_symptom(state["symptom_id"], state["answers"])
            cl.user_session.set("symptom_state", None)
            color = {"emergency": "🚨", "urgent": "⚠️", "soon": "📋", "routine": "📅", "self_care": "🏠"}.get(result.get("urgency", ""), "")
            msg = f"{color} **Result: {result.get('symptom', '')}**\n\n**Urgency:** {result.get('urgency_message', '')}\n**Doctor:** {result.get('doctor_recommended', 'General').title()}\n\n{result.get('message', '')}"
            if result.get("self_care"):
                msg += f"\n\n**Home Care:** {result['self_care']}"
            await cl.Message(content=msg, actions=card_grid() + sidebar_toggle())
        else:
            q = follow_ups[state["current_q"]]["question"]
            cl.user_session.set("symptom_state", state)
            await cl.Message(content=f"**Q{state['current_q']+1}:** {q}\n\nType: `yes` or `no`")
        return

    # ─── Keyword routing for sidebar dashboards ───
    if any(w in lower for w in ["doctor", "specialist", "who are"]):
        await on_card_doctors(None)
        return
    if any(w in lower for w in ["book", "appointment", "schedule"]):
        await on_card_book(None)
        return
    if any(w in lower for w in ["service", "fee", "cost", "price"]):
        await on_card_services(None)
        return
    if any(w in lower for w in ["insurance", "cashless", "star health", "icici"]):
        await on_card_insurance(None)
        return
    if any(w in lower for w in ["location", "where", "direction", "address", "hour"]):
        await update_sidebar("home")
        await cl.Message(content=f"📍 **{settings.clinic_address}**\n\n**Hours:** {settings.clinic_hours}\n**Phone:** {settings.clinic_phone}", actions=card_grid() + sidebar_toggle())
        return
    if any(w in lower for w in ["emergency", "urgent", "ambulance"]):
        await on_card_emergency(None)
        return
    if any(w in lower for w in ["symptom", "feel sick", "not well", "check symptom"]):
        await on_card_symptoms(None)
        return
    if any(w in lower for w in ["tip", "health tip", "advice"]):
        await on_card_tips(None)
        return
    if any(w in lower for w in ["profile", "my data", "my info"]):
        await on_card_profile(None)
        return
    if any(w in lower for w in ["analytics", "stats", "dashboard"]):
        await on_card_stats(None)
        return
    if any(w in lower for w in ["menu", "home", "start over"]):
        await on_card_home(None)
        return

    # ─── Sentiment ───
    sentiment = sentiment_analyzer.analyze(user_msg)
    intents_log.append("general")
    sentiments_log.append(sentiment.get("score", 0.5))
    cl.user_session.set("intents_log", intents_log)
    cl.user_session.set("sentiments_log", sentiments_log)

    if sentiment.get("should_escalate"):
        await cl.Message(content="I understand your frustration. 📞 **+91 98765 43210** | 📧 info@carefirstmedical.in", actions=card_grid() + sidebar_toggle())
        return

    # ─── RAG fallback ───
    async with cl.Message(content="Thinking...").send() as final_msg:
        try:
            result = await rag_engine.query(user_msg)
            answer = result.get("answer", "I'm not sure. Try using the navigation above.")
            sources = result.get("sources", [])
            if sources:
                answer += "\n\n*Sources: " + ", ".join(set(s["source"].split("/")[-1] for s in sources[:3])) + "*"
            final_msg.content = answer
            cl.user_session.set("conversation_history", history + [{"role": "user", "content": user_msg}, {"role": "assistant", "content": answer}])
        except Exception as e:
            logger.error(f"RAG error: {e}")
            final_msg.content = "I'm having trouble. Please try the navigation buttons above."


# ══════════════════════════════════════════════════════════════
# CHAT END
# ══════════════════════════════════════════════════════════════

@cl.on_chat_end
async def on_chat_end():
    session_start = cl.user_session.get("session_start", time.time())
    message_count = cl.user_session.get("message_count", 0)
    duration = time.time() - session_start
    session_id = cl.user_session.get("session_id", "unknown")
    intents = cl.user_session.get("intents_log", [])
    sentiments = cl.user_session.get("sentiments_log", [])
    log_session(session_id, message_count, duration, intents, sentiments)
    logger.info(f"Session ended | Messages: {message_count} | Duration: {duration:.1f}s")
