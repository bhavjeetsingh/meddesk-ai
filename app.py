"""
MedDesk AI - Modern Chatbot-First UI
Chatbot is primary interface with interactive card options.
Sidebar has card tiles as alternative access.
"""
import chainlit as cl
from config import get_settings
from core.rag_engine import CareFirstRAG
from core.intent_detector import IntentDetector
from core.sentiment import SentimentAnalyzer
from core.database import init_db, seed_data, get_user_by_username, verify_password, create_user
from core.health_tips import get_daily_tips, get_seasonal_tip, get_all_categories, get_tips_by_category, get_personalized_tips, get_tips_for_symptoms
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
# DATABASE INIT (runs at startup, before login page)
# ══════════════════════════════════════════════════════════════

import asyncio

async def _init_db_at_startup():
    """Initialize DB and seed users at app startup"""
    pass  # DB and RAG already initialized at startup
    logger.info("Database and RAG initialized at startup")

try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_init_db_at_startup())
    else:
        loop.run_until_complete(_init_db_at_startup())
except RuntimeError:
    asyncio.run(_init_db_at_startup())


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION
# ══════════════════════════════════════════════════════════════

@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    """Authenticate user with username and password"""
    user = await get_user_by_username(username)
    if user and user.is_active and verify_password(password, user.hashed_password):
        return cl.User(
            identifier=user.username,
            metadata={
                "role": user.role,
                "full_name": user.full_name,
                "email": user.email,
                "provider": "credentials"
            }
        )
    return None


# ══════════════════════════════════════════════════════════════
# SIGNUP PAGE (Custom Route via Starlette)
# ══════════════════════════════════════════════════════════════

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.routing import Route

SIGNUP_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Up - MedDesk AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #e0e0e0;
        }
        .container {
            background: rgba(30, 30, 50, 0.95);
            border-radius: 16px;
            padding: 40px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .logo { text-align: center; margin-bottom: 8px; font-size: 40px; }
        h1 { text-align: center; font-size: 22px; margin-bottom: 4px; color: #fff; }
        .subtitle { text-align: center; color: #888; font-size: 13px; margin-bottom: 28px; }
        .form-group { margin-bottom: 18px; }
        label { display: block; font-size: 13px; color: #aaa; margin-bottom: 6px; font-weight: 500; }
        input, select {
            width: 100%;
            padding: 12px 14px;
            border: 1px solid #333;
            border-radius: 8px;
            background: #1a1a2e;
            color: #fff;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        input:focus, select:focus { outline: none; border-color: #4a9eff; }
        input::placeholder { color: #555; }
        .btn {
            width: 100%;
            padding: 13px;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 8px;
            transition: transform 0.1s;
        }
        .btn:active { transform: scale(0.98); }
        .btn-primary { background: #4a9eff; color: #fff; }
        .btn-primary:hover { background: #3a8eef; }
        .error { background: rgba(231,76,60,0.15); border: 1px solid rgba(231,76,60,0.3); color: #e74c3c; padding: 10px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; display: none; }
        .error.show { display: block; }
        .footer { text-align: center; margin-top: 20px; font-size: 13px; color: #666; }
        .footer a { color: #4a9eff; text-decoration: none; }
        .footer a:hover { text-decoration: underline; }
        .divider { display: flex; align-items: center; margin: 20px 0; color: #555; font-size: 12px; }
        .divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #333; }
        .divider::before { margin-right: 12px; }
        .divider::after { margin-left: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🏥</div>
        <h1>MedDesk AI</h1>
        <p class="subtitle">Create your account</p>
        
        <div class="error" id="error-msg"></div>
        
        <form id="signup-form" onsubmit="return handleSubmit(event)">
            <div class="form-group">
                <label for="full_name">Full Name</label>
                <input type="text" id="full_name" name="full_name" placeholder="e.g. Amit Patel" required>
            </div>
            
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" placeholder="e.g. amit@email.com" required>
            </div>
            
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Choose a username" required minlength="3">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Min 6 characters" required minlength="6">
            </div>
            
            <div class="form-group">
                <label for="role">I am a</label>
                <select id="role" name="role">
                    <option value="patient">Patient</option>
                    <option value="staff">Staff Member</option>
                </select>
            </div>
            
            <button type="submit" class="btn btn-primary" id="submit-btn">Create Account</button>
        </form>
        
        <div class="footer">
            Already have an account? <a href="/">Sign In</a>
        </div>
    </div>
    
    <script>
        async function handleSubmit(e) {
            e.preventDefault();
            const btn = document.getElementById('submit-btn');
            const errDiv = document.getElementById('error-msg');
            btn.textContent = 'Creating account...';
            btn.disabled = true;
            errDiv.classList.remove('show');
            
            const data = {
                full_name: document.getElementById('full_name').value,
                email: document.getElementById('email').value,
                username: document.getElementById('username').value,
                password: document.getElementById('password').value,
                role: document.getElementById('role').value
            };
            
            try {
                const resp = await fetch('/auth/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await resp.json();
                
                if (result.success) {
                    window.location.href = '/?signup=success';
                } else {
                    errDiv.textContent = result.error || 'Signup failed';
                    errDiv.classList.add('show');
                    btn.textContent = 'Create Account';
                    btn.disabled = false;
                }
            } catch (err) {
                errDiv.textContent = 'Connection error. Please try again.';
                errDiv.classList.add('show');
                btn.textContent = 'Create Account';
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""


async def signup_page(request: Request):
    """Serve the signup page"""
    return HTMLResponse(SIGNUP_HTML)


async def signup_handler(request: Request):
    """Handle signup form submission"""
    try:
        body = await request.json()
        
        username = body.get("username", "").strip()
        email = body.get("email", "").strip()
        password = body.get("password", "")
        full_name = body.get("full_name", "").strip()
        role = body.get("role", "patient")
        
        # Validation
        if not username or len(username) < 3:
            return JSONResponse({"success": False, "error": "Username must be at least 3 characters"})
        if not email or "@" not in email:
            return JSONResponse({"success": False, "error": "Please enter a valid email"})
        if not password or len(password) < 6:
            return JSONResponse({"success": False, "error": "Password must be at least 6 characters"})
        if not full_name:
            return JSONResponse({"success": False, "error": "Please enter your full name"})
        if role not in ["patient", "staff"]:
            return JSONResponse({"success": False, "error": "Invalid role"})
        
        result = await create_user(username, email, password, full_name, role)
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return JSONResponse({"success": False, "error": "An error occurred. Please try again."})


# Add signup routes via middleware (runs BEFORE Chainlit's catch-all)
from chainlit.server import app as starlette_app
from starlette.middleware.base import BaseHTTPMiddleware

class SignupMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/auth/signup":
            if request.method == "GET":
                return HTMLResponse(SIGNUP_HTML)
            elif request.method == "POST":
                return await signup_handler(request)
        return await call_next(request)

starlette_app.add_middleware(SignupMiddleware)


# ══════════════════════════════════════════════════════════════
# LLM CONVERSATIONAL RESPONSES
# ══════════════════════════════════════════════════════════════

async def llm_chat(user_msg: str, system_prompt: str, chat_history: list = None) -> str:
    """Get a conversational response from the LLM"""
    from langchain_core.messages import HumanMessage, AIMessage
    
    messages = [("system", system_prompt)]
    
    if chat_history:
        for msg in chat_history[-6:]:
            if isinstance(msg, HumanMessage):
                messages.append(("human", msg.content))
            elif isinstance(msg, AIMessage):
                messages.append(("assistant", msg.content))
    
    messages.append(("human", user_msg))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | rag_engine.llm | StrOutputParser()
    
    try:
        return await chain.ainvoke({})
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        return ""


CONVERSATIONAL_SYSTEM_PROMPT = """You are MedDesk AI, a friendly and professional AI health assistant at MedDesk AI in Mumbai, India.

Your personality:
- Warm, empathetic, and helpful
- Use a mix of English and occasional Hindi words (namaste, dhanyavaad) for warmth
- Always be professional but conversational
- Ask clarifying questions when needed
- Never provide medical diagnoses - always recommend seeing a doctor

When someone describes symptoms:
1. Acknowledge their concern empathetically
2. Ask clarifying questions if needed (duration, severity)
3. Recommend the appropriate specialist
4. Offer to book an appointment

When someone greets you:
- Respond warmly and ask how you can help
- Mention you can help with appointments, doctors, symptoms, etc.

Available doctors and their specialties:
- Dr. Priya Sharma - General Practice (₹1,000) - Mon-Sat
- Dr. Rajesh Mehta - Cardiology (₹1,500) - Mon, Wed, Fri, Sat
- Dr. Anita Desai - Dermatology (₹1,200) - Mon-Fri
- Dr. Vikram Patel - Orthopedics (₹1,500) - Mon-Sat
- Dr. Sunita Reddy - Pediatrics (₹1,000) - Mon-Sat

Clinic hours: Mon-Sat 9:00 AM - 9:00 PM, Sun 10:00 AM - 2:00 PM
Phone: +91 98765 43210

IMPORTANT: Keep responses concise (2-4 sentences max). Always end with a helpful suggestion or question."""


SYMPTOM_CONSULT_PROMPT = """You are MedDesk AI, a medical receptionist AI. The patient is describing symptoms.

Your task:
1. Show empathy for their discomfort
2. Based on their symptoms, recommend the MOST appropriate specialist from:
   - General Practice (Dr. Priya Sharma) - for fever, cold, cough, general illness, stomach issues
   - Cardiology (Dr. Rajesh Mehta) - for chest pain, heart palpitations, blood pressure
   - Dermatology (Dr. Anita Desai) - for skin rashes, acne, hair loss, skin issues
   - Orthopedics (Dr. Vikram Patel) - for bone/joint pain, back pain, fractures, sports injuries
   - Pediatrics (Dr. Sunita Reddy) - for children's health issues

3. Ask one clarifying question if needed (duration, severity)
4. Offer to book an appointment with that doctor

Keep response to 2-3 sentences. Be warm and professional. End with "Would you like me to book an appointment with [doctor name]?" """


# ══════════════════════════════════════════════════════════════
# CARD GRID ACTIONS (Main navigation in chat)
# ══════════════════════════════════════════════════════════════

def card_grid():
    """Main card grid for chatbot navigation"""
    return [
        cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
        cl.Action(name="card_manage", label="🔄 Manage Appointments", payload={"card": "manage"}),
        cl.Action(name="card_symptoms", label="🔍 Check Symptoms", payload={"card": "symptoms"}),
        cl.Action(name="card_symptom_chat", label="💬 Ask About Symptoms", payload={"card": "symptom_chat"}),
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
    return []


def doctor_cards():
    """Doctor selection cards for booking"""
    return [
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Priya Sharma - General ₹1,000", payload={"doctor": "priya"}),
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Rajesh Mehta - Cardiology ₹1,500", payload={"doctor": "rajesh"}),
        cl.Action(name="select_doctor", label="👩‍⚕️ Dr. Anita Desai - Dermatology ₹1,200", payload={"doctor": "anita"}),
        cl.Action(name="select_doctor", label="👨‍⚕️ Dr. Vikram Patel - Orthopedics ₹1,500", payload={"doctor": "vikram"}),
        cl.Action(name="select_doctor", label="👩‍⚕️ Dr. Sunita Reddy - Pediatrics ₹1,000", payload={"doctor": "sunita"}),
    ] + back_button()


async def get_doctor_cards_with_slots():
    """Doctor selection cards with next available slots"""
    doctors = [
        {"key": "priya", "name": "Dr. Priya Sharma", "specialty": "General", "fee": 1000, "id": 1, "emoji": "👨‍⚕️"},
        {"key": "rajesh", "name": "Dr. Rajesh Mehta", "specialty": "Cardiology", "fee": 1500, "id": 2, "emoji": "👨‍⚕️"},
        {"key": "anita", "name": "Dr. Anita Desai", "specialty": "Dermatology", "fee": 1200, "id": 3, "emoji": "👩‍⚕️"},
        {"key": "vikram", "name": "Dr. Vikram Patel", "specialty": "Orthopedics", "fee": 1500, "id": 4, "emoji": "👨‍⚕️"},
        {"key": "sunita", "name": "Dr. Sunita Reddy", "specialty": "Pediatrics", "fee": 1000, "id": 5, "emoji": "👩‍⚕️"},
    ]
    
    cards = []
    for doc in doctors:
        next_slot = await appointment_system.get_next_available(doc["id"], days_ahead=3)
        slot_text = f" | Next: {next_slot['time']}" if next_slot else ""
        cards.append(
            cl.Action(
                name="select_doctor",
                label=f"{doc['emoji']} {doc['name']} - {doc['specialty']} ₹{doc['fee']}{slot_text}",
                payload={"doctor": doc["key"]}
            )
        )
    
    return cards + back_button()


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
        cl.Action(name="profile_action", label="📋 My Appointments", payload={"action": "appointments"}),
        cl.Action(name="profile_action", label="✏️ Update Profile", payload={"action": "update"}),
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

### 📢 What's New
- 🆕 Online booking now available!
- 💉 Flu vaccines in stock
- 📱 Teleconsultation services launched

---

### ⏱️ Current Wait Times
| Doctor | Est. Wait |
|--------|-----------|
| Dr. Priya Sharma | ~15 min |
| Dr. Rajesh Mehta | ~25 min |
| Dr. Anita Desai | ~20 min |
| Dr. Vikram Patel | ~30 min |
| Dr. Sunita Reddy | ~10 min |

*Wait times are approximate*

---

### Quick Actions
Click the cards in the chat or type:
- `book appointment` — Schedule a visit
- `cancel appointment` — Cancel a booking
- `reschedule appointment` — Change a booking
- `doctors` — Meet our specialists  
- `insurance` — Check your coverage
- `services` — View all services
- `emergency` — Urgent help

---

### 💡 Did You Know?
You can describe your symptoms in natural language and I'll recommend the right doctor!""", name="home_dashboard")
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

**💡 Tip:** Type your symptoms and I'll recommend the right doctor!

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
    pass  # DB and RAG already initialized at startup

    # Get logged-in user info
    user = cl.user_session.get("user")
    user_name = user.metadata.get("full_name", "Guest") if user else "Guest"
    user_role = user.metadata.get("role", "guest") if user else "guest"

    cl.user_session.set("conversation_history", [])
    cl.user_session.set("patient_info", {"name": user_name, "role": user_role})
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
    # Check for existing patient conditions
    patient = cl.user_session.get("patient_info", {})
    conditions = patient.get("conditions", [])
    tips_hint = ""
    if conditions:
        tips = get_personalized_tips(conditions, 2)
        tips_text = "\n".join([f"- {t['title']}: {t['tip'][:80]}..." for t in tips])
        tips_hint = f"\n\n**Your Health Tips:**\n{tips_text}"
    
    await cl.Message(
        content=f"## Welcome to {settings.clinic_name}\n\n"
                f"Namaste **{user_name}**! I'm **MedDesk AI** — your virtual health assistant.\n\n"
                f"I can help you with:\n"
                f"- Book appointments with our specialists\n"
                f"- Check symptoms and get doctor recommendations\n"
                f"- View services and pricing\n"
                f"- Insurance and payment information\n"
                f"- Cancel or reschedule existing appointments"
                f"{tips_hint}\n\n"
                f"**How can I help you today?** Click a card below or type your question:",
        actions=card_grid()
    ).send()


# ══════════════════════════════════════════════════════════════
# CARD ACTION HANDLERS
# ══════════════════════════════════════════════════════════════

@cl.action_callback("card_home")
async def on_card_home(action):
    cl.user_session.set("current_flow", None)
    cl.user_session.set("booking_state", None)
    cl.user_session.set("reschedule_state", None)
    await update_sidebar("home")
    await cl.Message(
        content="## 🏥 Home\n\nChoose an option below:",
        actions=card_grid()
    ).send()


@cl.action_callback("card_back")
async def on_card_back(action):
    cl.user_session.set("current_flow", None)
    cl.user_session.set("booking_state", None)
    cl.user_session.set("reschedule_state", None)
    await update_sidebar("home")
    await cl.Message(
        content="## 🏥 Main Menu\n\nChoose an option below:",
        actions=card_grid()
    ).send()


@cl.action_callback("toggle_sidebar")
async def on_toggle_sidebar(action):
    """Refresh sidebar content"""
    await update_sidebar("home")


@cl.action_callback("card_book")
async def on_card_book(action):
    await update_sidebar("doctors")
    cl.user_session.set("current_flow", "booking")
    cards = await get_doctor_cards_with_slots()
    await cl.Message(
        content="## 📅 Book Appointment\n\n**Step 1: Choose a doctor:**\n\n*Next available slots shown for each doctor*",
        actions=cards
    ).send()


@cl.action_callback("card_manage")
async def on_card_manage(action):
    await cl.Message(
        content="## 🔄 Manage Appointments\n\nI can help you cancel or reschedule your appointment.\n\n"
                "Please enter your **appointment ID** (e.g., `1` or `#1`).\n\n"
                "💡 **Tip:** You can find your appointment ID in your booking confirmation SMS.",
        actions=back_button()
    ).send()
    cl.user_session.set("current_flow", "manage appointment")


@cl.action_callback("cancel_appointment")
async def on_cancel_appointment(action):
    appt_id = action.payload.get("appointment_id")
    
    # Ask for confirmation first
    await cl.Message(
        content=f"## ❌ Cancel Appointment #{appt_id}\n\n"
                f"Are you sure you want to cancel this appointment?\n\n"
                f"This action cannot be undone.",
        actions=[
            cl.Action(name="confirm_cancel", label="✅ Yes, Cancel", payload={"appointment_id": appt_id}),
            cl.Action(name="card_manage", label="❌ No, Keep It", payload={"card": "manage"}),
        ]
    ).send()


@cl.action_callback("confirm_cancel")
async def on_confirm_cancel(action):
    appt_id = action.payload.get("appointment_id")
    result = await appointment_system.cancel_appointment(int(appt_id))
    if result.get("success"):
        await cl.Message(
            content=f"## ✅ Appointment Cancelled\n\n"
                    f"**Appointment #{appt_id}** with {result.get('doctor_name', '')} on {result.get('date', '')} has been **cancelled**.\n\n"
                    f"**What would you like to do next?**",
            actions=[
                cl.Action(name="card_book", label="📅 Book New Appointment", payload={"card": "book"}),
                cl.Action(name="card_home", label="🏠 Return to Menu", payload={"card": "home"}),
            ]
        ).send()
    else:
        await cl.Message(
            content=f"⚠️ Could not cancel: {result.get('error', 'Unknown error')}",
            actions=back_button()
        ).send()


@cl.action_callback("reschedule_appointment")
async def on_reschedule_appointment(action):
    appt_id = action.payload.get("appointment_id")
    doctor_id = action.payload.get("doctor_id")
    cl.user_session.set("reschedule_state", {
        "appointment_id": int(appt_id),
        "doctor_id": int(doctor_id),
        "step": "date"
    })
    await cl.Message(
        content=f"## 🔄 Reschedule Appointment #{appt_id}\n\n**Step 1: Choose a new date:**",
        actions=[
            cl.Action(name="reschedule_select_date", label="📅 Today", payload={"date": "today"}),
            cl.Action(name="reschedule_select_date", label="📅 Tomorrow", payload={"date": "tomorrow"}),
            cl.Action(name="reschedule_select_date", label="📅 This Week", payload={"date": "week"}),
        ] + back_button()
    ).send()


@cl.action_callback("reschedule_select_date")
async def on_reschedule_select_date(action):
    date_option = action.payload.get("date")
    state = cl.user_session.get("reschedule_state", {})

    if date_option == "today":
        target_date = date.today()
    elif date_option == "tomorrow":
        target_date = date.today() + timedelta(days=1)
    else:
        target_date = date.today() + timedelta(days=3)

    # Get available slots for that doctor on that date
    doctor_id = state.get("doctor_id", 1)
    slots = await appointment_system.get_available_slots(doctor_id, target_date)

    if not slots:
        await cl.Message(
            content=f"## 📅 No Slots Available\n\nNo available slots on **{target_date.strftime('%A, %B %d, %Y')}**.\n\nPlease choose another date.",
            actions=[
                cl.Action(name="reschedule_select_date", label="📅 Today", payload={"date": "today"}),
                cl.Action(name="reschedule_select_date", label="📅 Tomorrow", payload={"date": "tomorrow"}),
                cl.Action(name="reschedule_select_date", label="📅 This Week", payload={"date": "week"}),
            ] + back_button()
        ).send()
        return

    state["date"] = target_date
    cl.user_session.set("reschedule_state", state)

    slot_actions = [
        cl.Action(name="reschedule_select_time", label=f"🕐 {s['time']}", payload={"time": s["datetime"]})
        for s in slots[:8]
    ]

    await cl.Message(
        content=f"## 🔄 Reschedule — Choose Time\n\n**Date:** {target_date.strftime('%A, %B %d, %Y')}\n\n**Available slots:**",
        actions=slot_actions + back_button()
    ).send()


@cl.action_callback("reschedule_select_time")
async def on_reschedule_select_time(action):
    new_dt_str = action.payload.get("time")
    state = cl.user_session.get("reschedule_state", {})
    appt_id = state.get("appointment_id")

    new_datetime = datetime.fromisoformat(new_dt_str)
    result = await appointment_system.reschedule_appointment(appt_id, new_datetime)

    cl.user_session.set("reschedule_state", None)

    if result.get("success"):
        await cl.Message(
            content=f"## ✅ Appointment Rescheduled\n\n"
                    f"**Appointment #{appt_id}** has been moved:\n\n"
                    f"| | |\n|---|---|\n| 👨‍⚕️ **Doctor** | {result.get('doctor_name', '')} |\n"
                    f"| 📅 **New Date** | {result.get('new_datetime', '')} |\n\n"
                    f"Would you like to do anything else?",
            actions=card_grid()
        ).send()
    else:
        await cl.Message(
            content=f"⚠️ Could not reschedule: {result.get('error', 'Unknown error')}",
            actions=back_button()
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
    
    # Fetch actual available slots from database
    doctor_id = booking.get("doctor_id", 1)
    slots = await appointment_system.get_available_slots(doctor_id, appt_date)
    
    if not slots:
        await cl.Message(
            content=f"## 📅 No Slots Available\n\n"
                    f"**{booking.get('doctor', 'Doctor')}** has no available slots on "
                    f"**{appt_date.strftime('%A, %B %d, %Y')}**.\n\n"
                    f"Please choose another date.",
            actions=[
                cl.Action(name="select_date", label="📅 Today", payload={"date": "today"}),
                cl.Action(name="select_date", label="📅 Tomorrow", payload={"date": "tomorrow"}),
                cl.Action(name="select_date", label="📅 This Week", payload={"date": "week"}),
            ] + back_button()
        ).send()
        return
    
    booking["date"] = appt_date.isoformat()
    booking["step"] = "time"
    cl.user_session.set("booking_state", booking)
    
    # Show available time slots as buttons (max 8)
    slot_actions = [
        cl.Action(name="select_time", label=f"🕐 {s['time']}", payload={"time": s["datetime"], "time_label": s["time"]})
        for s in slots[:8]
    ]
    
    # If more than 8 slots, add a note
    extra_note = f"\n\n*({len(slots) - 8} more slots available)*" if len(slots) > 8 else ""
    
    await cl.Message(
        content=f"## 📅 Book Appointment\n\n"
                f"**Doctor:** {booking['doctor']}\n"
                f"**Date:** {appt_date.strftime('%A, %B %d, %Y')}\n\n"
                f"**Step 2: Choose a time slot:**{extra_note}",
        actions=slot_actions + back_button()
    ).send()


@cl.action_callback("select_time")
async def on_select_time(action):
    time_str = action.payload.get("time")
    time_label = action.payload.get("time_label")
    booking = cl.user_session.get("booking_state", {})
    
    booking["time"] = time_str
    booking["time_label"] = time_label
    booking["step"] = "confirm"
    cl.user_session.set("booking_state", booking)
    
    date_raw = booking.get("date", date.today().isoformat())
    appt_date = date.fromisoformat(date_raw) if isinstance(date_raw, str) else date_raw
    fee = booking.get("fee", 1000)
    gst = int(fee * 0.18)
    
    await cl.Message(
        content=f"## 📅 Book Appointment\n\n"
                f"**Doctor:** {booking['doctor']} ({booking['specialty']})\n"
                f"**Date:** {appt_date.strftime('%A, %B %d, %Y')}\n"
                f"**Time:** {time_label}\n"
                f"**Fee:** ₹{fee} (+18% GST = ₹{fee + gst} total)\n\n"
                f"**Step 3: Confirm booking**\n\n"
                f"Please share your **name and phone number** to confirm.",
        actions=back_button()
    ).send()


@cl.action_callback("card_symptom_chat")
async def on_card_symptom_chat(action):
    cl.user_session.set("current_flow", "symptom_chat")
    await cl.Message(
        content="## Symptom Consultation\n\n**Describe your symptoms in plain language.**\n\nExamples:\n- I have been having headaches for 3 days\n- My chest hurts when I breathe\n- I have a rash on my arm\n- I feel dizzy and nauseous\n\nI'll recommend the right specialist for you!",
        actions=back_button()
    ).send()


@cl.action_callback("card_symptoms")
async def on_card_symptoms(action):
    await update_sidebar("symptoms")
    cl.user_session.set("current_flow", "symptoms")
    await cl.Message(
        content="## Symptom Checker\n\n**Select your symptom:**",
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
            actions=back_button()
        ).send()
    else:
        result = evaluate_symptom(symptom_id, [])
        color = {"emergency": "🚨", "urgent": "⚠️", "soon": "📋", "routine": "📅", "self_care": "🏠"}.get(result.get("urgency", ""), "")
        msg = f"{color} **Result: {result.get('symptom', '')}**\n\n**Urgency:** {result.get('urgency_message', '')}\n**Doctor:** {result.get('doctor_recommended', 'General').title()}\n\n{result.get('message', '')}"
        if result.get("self_care"):
            msg += f"\n\n**Home Care:** {result['self_care']}"
        msg += "\n\n**What would you like to do next?**"
        
        # Suggest relevant actions based on urgency
        suggested_actions = []
        if result.get("urgency") in ["emergency", "urgent"]:
            suggested_actions = [
                cl.Action(name="card_emergency", label="🚨 Emergency Help", payload={"card": "emergency"}),
                cl.Action(name="card_book", label="📅 Book Urgent Visit", payload={"card": "book"}),
            ]
        else:
            suggested_actions = [
                cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
                cl.Action(name="card_tips", label="💡 Health Tips", payload={"card": "tips"}),
            ]
        
        await cl.Message(content=msg, actions=suggested_actions + card_grid()).send()


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
    
    # Get next available slot for each doctor in this specialty
    doctors_info = {
        "General": {
            "name": "Dr. Priya Sharma",
            "specialty": "General Practice",
            "qualification": "MBBS, MD (Medicine)",
            "experience": "10+ years",
            "fee": 1000,
            "doctor_id": 1,
            "available_days": "Mon-Sat",
            "specialties": "Preventive healthcare, Diabetes, Women's health"
        },
        "Cardiology": {
            "name": "Dr. Rajesh Mehta",
            "specialty": "Cardiology",
            "qualification": "MBBS, MD (Cardiology), DM",
            "experience": "15+ years",
            "fee": 1500,
            "doctor_id": 2,
            "available_days": "Mon, Wed, Fri, Sat",
            "specialties": "Interventional cardiology, Heart failure, Preventive cardiology"
        },
        "Dermatology": {
            "name": "Dr. Anita Desai",
            "specialty": "Dermatology",
            "qualification": "MBBS, MD (Dermatology)",
            "experience": "8+ years",
            "fee": 1200,
            "doctor_id": 3,
            "available_days": "Mon-Fri",
            "specialties": "Cosmetic dermatology, Acne treatment, Laser therapy"
        },
        "Orthopedics": {
            "name": "Dr. Vikram Patel",
            "specialty": "Orthopedics",
            "qualification": "MBBS, MS (Orthopedics)",
            "experience": "12+ years",
            "fee": 1500,
            "doctor_id": 4,
            "available_days": "Mon-Sat",
            "specialties": "Joint replacement, Sports injuries, Spinal disorders"
        },
        "Pediatrics": {
            "name": "Dr. Sunita Reddy",
            "specialty": "Pediatrics",
            "qualification": "MBBS, MD (Pediatrics)",
            "experience": "7+ years",
            "fee": 1000,
            "doctor_id": 5,
            "available_days": "Mon-Sat",
            "specialties": "Newborn care, Vaccinations, Developmental pediatrics"
        }
    }
    
    doc = doctors_info.get(specialty)
    if not doc:
        await cl.Message(content="Doctor information not available.", actions=specialty_cards()).send()
        return
    
    # Get next available slot
    next_slot = await appointment_system.get_next_available(doc["doctor_id"], days_ahead=7)
    slot_text = f"\n\n**📅 Next Available:** {next_slot['day']}, {next_slot['date']} at {next_slot['time']}" if next_slot else "\n\n**📅 Next Available:** Check with reception"
    
    content = f"## {'🩺' if specialty == 'General' else '❤️' if specialty == 'Cardiology' else '🧴' if specialty == 'Dermatology' else '🦴' if specialty == 'Orthopedics' else '👶'} {doc['specialty']}\n\n"
    content += f"### {doc['name']}\n"
    content += f"- **Qualification:** {doc['qualification']}\n"
    content += f"- **Experience:** {doc['experience']}\n"
    content += f"- **Fee:** ₹{doc['fee']}\n"
    content += f"- **Available:** {doc['available_days']}\n"
    content += f"- **Specialties:** {doc['specialties']}"
    content += slot_text
    content += f"\n\n**What would you like to do?**"
    
    await cl.Message(
        content=content,
        actions=[
            cl.Action(name="card_book", label="📅 Book with " + doc['name'].split()[-1], payload={"card": "book"}),
            cl.Action(name="card_doctors", label="👨‍⚕️ View Other Doctors", payload={"card": "doctors"}),
        ] + back_button()
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
    patient = cl.user_session.get("patient_info", {})
    conditions = patient.get("conditions", [])
    
    if tip_type == "daily":
        if conditions:
            tips = get_personalized_tips(conditions, 3)
            header = "## Personalized Health Tips\n\n*Based on your profile:*\n\n"
        else:
            tips = get_daily_tips(3)
            header = "## Daily Health Tips\n\n"
        tip_text = "\n\n".join([f"**{t['title']}**\n{t['tip']}" for t in tips])
        content = header + tip_text
        if not conditions:
            content += "\n\n*Tip: Tell me about your health conditions for personalized tips!*"
    elif tip_type == "seasonal":
        seasonal = get_seasonal_tip()
        content = f"## Seasonal Tip\n\n**{seasonal['title']}**\n{seasonal['tip']}"
    else:
        categories = get_all_categories()
        content = "## Tips by Category\n\n" + "\n".join([f"- {c}" for c in categories])
    
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
        actions=back_button()
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
        actions = profile_cards()
    elif profile_action == "appointments":
        # Show appointment management
        await on_card_manage(None)
        return
    elif profile_action == "update":
        cl.user_session.set("awaiting_profile_update", True)
        content = "## ✏️ Update Profile\n\nPlease provide: `Name, Phone, Age, Gender`\n\nExample: `John Doe, 9876543210, 30, M`"
        actions = profile_cards()
    else:
        content = "## 📄 Prescription\n\nTo generate a prescription, provide:\n`PatientName, Age, Gender, Diagnosis, Medicine Dose Frequency Duration`\n\nExample: `Amit Patel, 35, M, Viral Fever, Paracetamol 500mg 3x/day 5days`"
        actions = profile_cards()
    
    await cl.Message(content=content, actions=actions).send()


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
    
    await cl.Message(content=content, actions=back_button()).send()


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
            doctor_id = booking_state.get("doctor_id", 1)
            fee = booking_state.get("fee", 1000)
            date_raw = booking_state.get("date", (date.today() + timedelta(days=1)).isoformat())
            appt_date = date.fromisoformat(date_raw) if isinstance(date_raw, str) else date_raw
            time_str = booking_state.get("time")
            time_label = booking_state.get("time_label", "")
            gst = int(fee * 0.18)
            
            # Parse the datetime from the selected time slot
            if time_str:
                appt_datetime = datetime.fromisoformat(time_str)
            else:
                appt_datetime = datetime.combine(appt_date, datetime.now().time().replace(hour=10, minute=0))
            
            # Extract patient info from message
            parts = [p.strip() for p in user_msg.split(",")]
            patient_name = parts[0] if parts else "Patient"
            patient_phone = phone_match.group(0) if phone_match else (parts[1] if len(parts) > 1 else "")
            
            # Actually book in database
            result = await appointment_system.book_appointment(
                patient_info={"first_name": patient_name.split()[0], "last_name": " ".join(patient_name.split()[1:]) if len(patient_name.split()) > 1 else "", "phone": patient_phone},
                doctor_id=doctor_id,
                appointment_datetime=appt_datetime,
                reason="Online booking"
            )
            
            if result.get("success"):
                appt_id = result.get("appointment_id", "N/A")
                await cl.Message(
                    content=f"## ✅ Appointment Confirmed!\n\n"
                            f"| | |\n|---|---|\n"
                            f"| 🎫 **Appointment ID** | #{appt_id} |\n"
                            f"| 👤 **Patient** | {patient_name} |\n"
                            f"| 👨‍⚕️ **Doctor** | {doctor} |\n"
                            f"| 📅 **Date** | {appt_date.strftime('%A, %B %d, %Y')} |\n"
                            f"| 🕐 **Time** | {time_label} |\n"
                            f"| 💰 **Total** | ₹{fee + gst} (incl. 18% GST) |\n\n"
                            f"📱 A confirmation SMS will be sent to **{patient_phone}**.\n\n"
                            f"**What would you like to do next?**",
                    actions=[
                        cl.Action(name="card_manage", label="🔄 View My Appointments", payload={"card": "manage"}),
                        cl.Action(name="card_book", label="📅 Book Another", payload={"card": "book"}),
                        cl.Action(name="card_tips", label="💡 Health Tips", payload={"card": "tips"}),
                    ]
                )
            else:
                await cl.Message(
                    content=f"⚠️ **Booking Failed:** {result.get('error', 'Unknown error')}\n\n"
                            f"Please try again or contact us at **{settings.clinic_phone}**.",
                    actions=doctor_cards()
                )
            
            cl.user_session.set("booking_state", None)
            return
        await cl.Message(content="Please share your **name and phone number** to confirm.\n\nExample: `Amit Patel, 9876543210`")
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
            msg += "\n\n**What would you like to do next?**"
            
            # Suggest relevant actions based on urgency
            suggested_actions = []
            if result.get("urgency") in ["emergency", "urgent"]:
                suggested_actions = [
                    cl.Action(name="card_emergency", label="🚨 Emergency Help", payload={"card": "emergency"}),
                    cl.Action(name="card_book", label="📅 Book Urgent Visit", payload={"card": "book"}),
                ]
            else:
                suggested_actions = [
                    cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
                    cl.Action(name="card_tips", label="💡 Health Tips", payload={"card": "tips"}),
                ]
            
            await cl.Message(content=msg, actions=suggested_actions + card_grid())
        else:
            q = follow_ups[state["current_q"]]["question"]
            cl.user_session.set("symptom_state", state)
            await cl.Message(content=f"**Q{state['current_q']+1}:** {q}\n\nType: `yes` or `no`")
        return

    # ─── Handle appointment management (cancel/reschedule) ───
    if cl.user_session.get("current_flow") == "manage appointment":
        # Try to extract appointment ID from message
        id_match = re.search(r'#?(\d+)', user_msg)
        if id_match:
            appt_id = int(id_match.group(1))
            appt = await appointment_system.get_appointment_by_id(appt_id)
            if appt and appt.get("status") in ["scheduled", "confirmed"]:
                cl.user_session.set("current_flow", None)
                await cl.Message(
                    content=f"## 📋 Appointment #{appt_id}\n\n"
                            f"| | |\n|---|---|\n| 👨‍⚕️ **Doctor** | {appt['doctor_name']} ({appt['specialty']}) |\n"
                            f"| 📅 **Date** | {appt['date']} at {appt['time']} |\n"
                            f"| 💰 **Fee** | {appt['fee']} |\n"
                            f"| 📌 **Status** | {appt['status'].title()} |\n\n"
                            f"**What would you like to do?**",
                    actions=[
                        cl.Action(name="cancel_appointment", label="❌ Cancel Appointment", payload={"appointment_id": appt_id}),
                        cl.Action(name="reschedule_appointment", label="🔄 Reschedule", payload={"appointment_id": appt_id, "doctor_id": appt["doctor_id"]}),
                    ] + back_button()
                ).send()
                return
            else:
                cl.user_session.set("current_flow", None)
                msg = f"⚠️ Appointment #{appt_id} not found or cannot be managed."
                if appt:
                    msg += f" (Status: {appt.get('status', 'unknown')})"
                await cl.Message(content=msg, actions=card_grid()).send()
                return
        else:
            await cl.Message(content="Please enter a valid **appointment ID** (e.g., `1` or `#1`).").send()
            return

    # ─── Keyword routing for sidebar dashboards ───
    # First, check for specific intents that should use LLM
    
    # Greetings - use conversational LLM
    greeting_words = ["hi", "hello", "hey", "namaste", "good morning", "good afternoon", "good evening"]
    if any(lower.startswith(g) or lower == g for g in greeting_words):
        history = cl.user_session.get("conversation_history", [])
        response = await llm_chat(user_msg, CONVERSATIONAL_SYSTEM_PROMPT, history)
        if response:
            await cl.Message(
                content=response,
                actions=[
                    cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
                    cl.Action(name="card_symptoms", label="🔍 Check Symptoms", payload={"card": "symptoms"}),
                    cl.Action(name="card_doctors", label="👨‍⚕️ Meet Doctors", payload={"card": "doctors"}),
                ]
            ).send()
            cl.user_session.set("conversation_history", history + [{"role": "user", "content": user_msg}, {"role": "assistant", "content": response}])
        return
    
    # Symptom descriptions - use LLM to recommend doctor
    symptom_keywords = ["pain", "hurt", "ache", "fever", "cough", "cold", "rash", "sick", "ill",
                        "headache", "stomach", "chest", "back", "joint", "skin", "acne", "hair loss",
                        "feel like", "having", "suffering from", "trouble with", "problem with",
                        "vomit", "nausea", "diarrhea", "constipation", "dizzy", "weak",
                        "breathing", "palpitation", "swelling", "infection", "allergy",
                        "insomnia", "anxiety", "depression", "stress", "fatigue",
                        "eye", "ear", "throat", "nose", "tooth", "dental"]
    if (any(s in lower for s in symptom_keywords) or cl.user_session.get("current_flow") == "symptom_chat") and not cl.user_session.get("symptom_state"):
        history = cl.user_session.get("conversation_history", [])
        response = await llm_chat(user_msg, SYMPTOM_CONSULT_PROMPT, history)
        if response:
            await cl.Message(
                content=response,
                actions=[
                    cl.Action(name="card_book", label="📅 Book Appointment", payload={"card": "book"}),
                    cl.Action(name="card_symptoms", label="🔍 Full Symptom Check", payload={"card": "symptoms"}),
                    cl.Action(name="card_doctors", label="👨‍⚕️ Meet Doctors", payload={"card": "doctors"}),
                ]
            ).send()
            cl.user_session.set("conversation_history", history + [{"role": "user", "content": user_msg}, {"role": "assistant", "content": response}])
        return
    
    # Now check for specific card-based intents
    if any(w in lower for w in ["doctor", "specialist", "who are"]):
        await on_card_doctors(None)
        return
    if any(w in lower for w in ["book", "appointment", "schedule"]):
        await on_card_book(None)
        return
    if any(w in lower for w in ["cancel", "reschedule", "change appointment", "manage appointment", "my appointment"]):
        await on_card_manage(None)
        return
    if any(w in lower for w in ["service", "fee", "cost", "price"]):
        await on_card_services(None)
        return
    if any(w in lower for w in ["insurance", "cashless", "star health", "icici"]):
        await on_card_insurance(None)
        return
    if any(w in lower for w in ["location", "where", "direction", "address", "hour"]):
        await update_sidebar("home")
        await cl.Message(content=f"📍 **{settings.clinic_address}**\n\n**Hours:** {settings.clinic_hours}\n**Phone:** {settings.clinic_phone}", actions=card_grid())
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
        await cl.Message(content="I understand your frustration. 📞 **+91 98765 43210** | 📧 info@carefirstmedical.in", actions=card_grid())
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
