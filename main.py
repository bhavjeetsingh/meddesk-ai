"""
CareFirst Medical Center - FastAPI Backend
REST API for the clinic receptionist system (Ollama - FREE)
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from config import get_settings
from core.rag_engine import CareFirstRAG
from core.database import init_db, seed_data
from tools.appointments import AppointmentSystem
from tools.clinic_tools import ClinicTools
from loguru import logger
import uvicorn


app = FastAPI(
    title="CareFirst Medical Center - API",
    description="AI-powered clinic receptionist with RAG, appointment booking, and more",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
settings = get_settings()
rag_engine = CareFirstRAG(settings)
appointment_system = AppointmentSystem(settings)
clinic_tools = ClinicTools(settings)


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    await init_db()
    await seed_data()
    await rag_engine.initialize()
    logger.info("CareFirst Medical Center API started successfully")


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    sentiment: str
    sources: Optional[List[Dict]] = None
    suggested_actions: Optional[List[str]] = None


class AppointmentRequest(BaseModel):
    patient_name: str
    patient_email: str
    patient_phone: str
    doctor_id: int
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    reason: Optional[str] = ""


class AvailabilityRequest(BaseModel):
    doctor_id: int
    date: str  # YYYY-MM-DD


# --- Chat Endpoints ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        result = await rag_engine.query(request.message)
        return ChatResponse(
            response=result["answer"],
            intent="general",
            confidence=0.9,
            sentiment="neutral",
            sources=result.get("sources", [])
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Appointment Endpoints ---

@app.get("/api/doctors")
async def get_doctors(specialty: Optional[str] = None):
    """Get list of doctors"""
    return await appointment_system.get_doctors(specialty)


@app.post("/api/availability")
async def get_availability(request: AvailabilityRequest):
    """Get available time slots"""
    try:
        target_date = date.fromisoformat(request.date)
        slots = await appointment_system.get_available_slots(
            request.doctor_id, target_date
        )
        return {"slots": slots, "date": request.date, "doctor_id": request.doctor_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/appointments/book")
async def book_appointment(request: AppointmentRequest):
    """Book an appointment"""
    try:
        dt = datetime.fromisoformat(f"{request.date}T{request.time}")
        result = await appointment_system.book_appointment(
            patient_info={
                "first_name": request.patient_name.split()[0],
                "last_name": " ".join(request.patient_name.split()[1:]) if len(request.patient_name.split()) > 1 else "",
                "email": request.patient_email,
                "phone": request.patient_phone
            },
            doctor_id=request.doctor_id,
            appointment_datetime=dt,
            reason=request.reason
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/appointments/{email}")
async def get_patient_appointments(email: str):
    """Get patient's appointments"""
    return await appointment_system.get_patient_appointments(email)


@app.delete("/api/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: int):
    """Cancel an appointment"""
    return await appointment_system.cancel_appointment(appointment_id)


# --- Clinic Info Endpoints ---

@app.get("/api/clinic/info")
async def get_clinic_info(topic: Optional[str] = None):
    """Get clinic information"""
    return {"info": clinic_tools.get_clinic_info(topic)}


@app.get("/api/clinic/services")
async def get_services(service: Optional[str] = None):
    """Get service information"""
    return {"services": clinic_tools.get_service_info(service)}


@app.get("/api/clinic/insurance/{provider}")
async def check_insurance(provider: str):
    """Check insurance acceptance"""
    return {"result": clinic_tools.check_insurance(provider)}


@app.get("/api/clinic/policies")
async def get_policies(policy: Optional[str] = None):
    """Get clinic policies"""
    return {"policies": clinic_tools.get_policies(policy)}


@app.get("/api/clinic/directions")
async def get_directions():
    """Get directions to clinic"""
    return {"directions": clinic_tools.get_directions()}


@app.get("/api/clinic/wait-times")
async def get_wait_times():
    """Get current wait times"""
    return clinic_tools.get_wait_times()


# --- RAG Endpoints ---

@app.post("/api/rag/search")
async def rag_search(query: str, k: int = 5):
    """Search knowledge base"""
    results = await rag_engine.search_similar(query, k)
    return {"results": results}


@app.get("/api/rag/stats")
async def rag_stats():
    """Get RAG statistics"""
    return await rag_engine.get_stats()


@app.post("/api/rag/upload")
async def upload_document(file_path: str):
    """Add document to knowledge base"""
    num_chunks = await rag_engine.add_document(file_path)
    return {"message": f"Added {num_chunks} chunks", "file": file_path}


# --- Health Check ---

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "CareFirst Medical Center",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
