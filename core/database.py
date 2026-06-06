"""
CareFirst Medical Center - Database Models & Connection
SQLite with async SQLAlchemy for patient/appointment storage
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    Float, ForeignKey, create_engine
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from typing import Optional
import enum


class Base(DeclarativeBase):
    pass


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(20), default="patient")  # admin, staff, doctor, patient
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    date_of_birth = Column(String(10), nullable=False)
    insurance_id = Column(String(50), nullable=True)
    insurance_provider = Column(String(100), nullable=True)
    emergency_contact = Column(String(200), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    medical_notes = Column(Text, nullable=True)
    abha_id = Column(String(20), nullable=True)  # Indian Health ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="patient")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    qualification = Column(String(200), nullable=False)  # MBBS, MD, etc.
    registration_number = Column(String(50), nullable=False)  # Medical Council
    bio = Column(Text, nullable=True)
    available_days = Column(String(100), nullable=False, default="Mon,Tue,Wed,Thu,Fri,Sat")
    slot_duration_minutes = Column(Integer, default=30)
    consultation_fee = Column(Integer, default=1000)  # In ₹
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    appointments = relationship("Appointment", back_populates="doctor")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    status = Column(String(20), default=AppointmentStatus.SCHEDULED.value)
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    room_number = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class ConversationLog(Base):
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    was_escalated = Column(Boolean, default=False)
    tools_used = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database Engine & Session
DATABASE_URL = "sqlite+aiosqlite:///./meddesk.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def hash_password(password: str) -> str:
    """Hash a password using passlib with bcrypt"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


async def get_user_by_username(username: str) -> Optional[User]:
    """Get a user by username"""
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()


async def create_user(username: str, email: str, password: str, full_name: str, role: str = "patient") -> dict:
    """Create a new user"""
    async with async_session() as session:
        from sqlalchemy import select
        
        # Check if username already exists
        existing = await session.execute(
            select(User).where(User.username == username)
        )
        if existing.scalar_one_or_none():
            return {"success": False, "error": "Username already exists"}
        
        # Check if email already exists
        existing_email = await session.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalar_one_or_none():
            return {"success": False, "error": "Email already registered"}
        
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return {
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "message": f"Account created for {full_name}"
        }


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for database sessions"""
    async with async_session() as session:
        yield session


async def seed_data():
    """Seed database with sample doctors, patients, and users (Indian Context)"""
    async with async_session() as session:
        from sqlalchemy import select, func
        
        # Seed users first
        result = await session.execute(select(func.count(User.id)))
        if result.scalar() == 0:
            users = [
                User(
                    username="admin",
                    email="admin@carefirstmedical.in",
                    hashed_password=hash_password("admin123"),
                    full_name="Admin User",
                    role="admin",
                    is_active=True
                ),
                User(
                    username="staff",
                    email="staff@carefirstmedical.in",
                    hashed_password=hash_password("staff123"),
                    full_name="Reception Staff",
                    role="staff",
                    is_active=True
                ),
                User(
                    username="doctor",
                    email="doctor@carefirstmedical.in",
                    hashed_password=hash_password("doctor123"),
                    full_name="Dr. Priya Sharma",
                    role="doctor",
                    is_active=True
                ),
                User(
                    username="patient",
                    email="patient@email.com",
                    hashed_password=hash_password("patient123"),
                    full_name="Amit Patel",
                    role="patient",
                    is_active=True
                ),
            ]
            session.add_all(users)
            await session.commit()

        # Check if doctors already exist
        result = await session.execute(select(func.count(Doctor.id)))
        if result.scalar() > 0:
            return

        # Sample Doctors - Indian Context
        doctors = [
            Doctor(
                first_name="Priya", last_name="Sharma",
                specialty="General Practice",
                email="dr.priya.sharma@carefirstmedical.in",
                phone="+91 98765 43201",
                qualification="MBBS, MD (Medicine)",
                registration_number="MCI/2015/12345",
                bio="Dr. Priya Sharma is a dedicated general physician with over 10 years of experience in primary care. She completed her MBBS from Grant Medical College, Mumbai and MD in Internal Medicine from KEM Hospital. She specializes in preventive healthcare, diabetes management, and women's health.",
                available_days="Mon,Tue,Wed,Thu,Fri,Sat",
                slot_duration_minutes=30,
                consultation_fee=1000
            ),
            Doctor(
                first_name="Rajesh", last_name="Mehta",
                specialty="Cardiology",
                email="dr.rajesh.mehta@carefirstmedical.in",
                phone="+91 98765 43202",
                qualification="MBBS, MD (Cardiology), DM",
                registration_number="MCI/2012/67890",
                bio="Dr. Rajesh Mehta is a senior cardiologist with 15+ years of experience. He completed his MBBS from Seth GS Medical College, MD from AIIMS Delhi, and DM in Cardiology. He specializes in interventional cardiology, heart failure management, and preventive cardiology.",
                available_days="Mon,Wed,Fri,Sat",
                slot_duration_minutes=45,
                consultation_fee=1500
            ),
            Doctor(
                first_name="Anita", last_name="Desai",
                specialty="Dermatology",
                email="dr.anita.desai@carefirstmedical.in",
                phone="+91 98765 43203",
                qualification="MBBS, MD (Dermatology)",
                registration_number="MCI/2014/11223",
                bio="Dr. Anita Desai is a board-certified dermatologist with 8+ years of experience. She completed her MBBS from Lady Hardinge Medical College, Delhi and MD in Dermatology from CMC Vellore. She specializes in cosmetic dermatology, acne treatment, skin cancer screening, and laser therapy.",
                available_days="Mon,Tue,Wed,Thu,Fri",
                slot_duration_minutes=30,
                consultation_fee=1200
            ),
            Doctor(
                first_name="Vikram", last_name="Patel",
                specialty="Orthopedics",
                email="dr.vikram.patel@carefirstmedical.in",
                phone="+91 98765 43204",
                qualification="MBBS, MS (Orthopedics)",
                registration_number="MCI/2013/44556",
                bio="Dr. Vikram Patel is an orthopedic surgeon with 12+ years of experience. He completed his MBBS from King Edward Memorial Hospital, Mumbai and MS in Orthopedics from PGI Chandigarh. He specializes in joint replacement, sports injuries, spinal disorders, and trauma surgery.",
                available_days="Mon,Tue,Wed,Thu,Fri,Sat",
                slot_duration_minutes=45,
                consultation_fee=1500
            ),
            Doctor(
                first_name="Sunita", last_name="Reddy",
                specialty="Pediatrics",
                email="dr.sunita.reddy@carefirstmedical.in",
                phone="+91 98765 43205",
                qualification="MBBS, MD (Pediatrics)",
                registration_number="MCI/2016/78901",
                bio="Dr. Sunita Reddy is a pediatrician with 7+ years of experience. She completed her MBBS from Osmania Medical College, Hyderabad and MD in Pediatrics from NIMS Hyderabad. She specializes in newborn care, childhood vaccinations, developmental pediatrics, and pediatric nutrition.",
                available_days="Mon,Tue,Wed,Thu,Fri,Sat",
                slot_duration_minutes=30,
                consultation_fee=1000
            ),
        ]
        session.add_all(doctors)

        # Sample Patients - Indian Context
        patients = [
            Patient(
                first_name="Amit", last_name="Patel",
                email="amit.patel@email.com", phone="+91 99887 76655",
                date_of_birth="1990-05-15",
                insurance_id="SH-12345678",
                insurance_provider="Star Health",
                emergency_contact="Sunita Patel",
                emergency_phone="+91 99887 76656",
                abha_id="1234-5678-9012"
            ),
            Patient(
                first_name="Neha", last_name="Kapoor",
                email="neha.kapoor@email.com", phone="+91 88776 65544",
                date_of_birth="1985-08-22",
                insurance_id="IL-87654321",
                insurance_provider="ICICI Lombard",
                emergency_contact="Rahul Kapoor",
                emergency_phone="+91 88776 65545"
            ),
        ]
        session.add_all(patients)

        # Sample Appointments
        from datetime import timedelta
        appointments = [
            Appointment(
                patient_id=1, doctor_id=1,
                appointment_date=datetime.now() + timedelta(days=1),
                status="scheduled", reason="General checkup"
            ),
            Appointment(
                patient_id=2, doctor_id=2,
                appointment_date=datetime.now() + timedelta(days=2),
                status="scheduled", reason="Heart consultation"
            ),
        ]
        session.add_all(appointments)

        await session.commit()
