"""
CareFirst Medical Center - Appointment Booking System
Handles scheduling, availability checking (Indian Context)
"""
from datetime import datetime, timedelta, date, time
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import Appointment, Doctor, Patient, AppointmentStatus, async_session
from loguru import logger


class AppointmentSystem:
    """Complete appointment management system (Indian Context)"""

    CLINIC_OPEN = time(9, 0)
    CLINIC_CLOSE = time(21, 0)
    SATURDAY_OPEN = time(9, 0)
    SATURDAY_CLOSE = time(21, 0)
    SUNDAY_OPEN = time(10, 0)
    SUNDAY_CLOSE = time(14, 0)

    def __init__(self, config):
        self.config = config

    async def get_available_slots(
        self,
        doctor_id: int,
        target_date: date,
        slot_duration: int = 30
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a doctor on a specific date"""
        async with async_session() as session:
            doctor = await session.get(Doctor, doctor_id)
            if not doctor:
                return []

            day_name = target_date.strftime("%a")
            if day_name not in doctor.available_days.split(","):
                return []

            # Set clinic hours based on day
            if day_name == "Sun":
                open_time, close_time = self.SUNDAY_OPEN, self.SUNDAY_CLOSE
            else:
                open_time, close_time = self.CLINIC_OPEN, self.CLINIC_CLOSE

            start_of_day = datetime.combine(target_date, open_time)
            end_of_day = datetime.combine(target_date, close_time)

            result = await session.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == doctor_id,
                        Appointment.appointment_date >= start_of_day,
                        Appointment.appointment_date < end_of_day,
                        Appointment.status.in_(["scheduled", "confirmed"])
                    )
                )
            )
            existing_appointments = result.scalars().all()

            all_slots = []
            current_time = start_of_day
            while current_time + timedelta(minutes=slot_duration) <= end_of_day:
                all_slots.append(current_time)
                current_time += timedelta(minutes=slot_duration)

            booked_times = {appt.appointment_date for appt in existing_appointments}

            available = []
            now = datetime.now()
            for slot in all_slots:
                if slot not in booked_times and slot > now:
                    available.append({
                        "datetime": slot.isoformat(),
                        "time": slot.strftime("%I:%M %p"),
                        "date": slot.strftime("%Y-%m-%d"),
                        "day": slot.strftime("%A"),
                        "doctor_id": doctor_id,
                        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                        "slot_duration": slot_duration
                    })

            return available

    async def get_next_available(
        self,
        doctor_id: int,
        days_ahead: int = 7
    ) -> Optional[Dict]:
        """Find the next available slot for a doctor"""
        today = date.today()
        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            slots = await self.get_available_slots(doctor_id, check_date)
            if slots:
                return slots[0]
        return None

    async def book_appointment(
        self,
        patient_info: Dict[str, Any],
        doctor_id: int,
        appointment_datetime: datetime,
        reason: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Book a new appointment"""
        async with async_session() as session:
            patient = await self._find_or_create_patient(session, patient_info)

            doctor = await session.get(Doctor, doctor_id)
            if not doctor:
                return {"success": False, "error": "Doctor not found"}

            existing = await session.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == doctor_id,
                        Appointment.appointment_date == appointment_datetime,
                        Appointment.status.in_(["scheduled", "confirmed"])
                    )
                )
            )
            if existing.scalar():
                return {"success": False, "error": "This slot is already booked"}

            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor_id,
                appointment_date=appointment_datetime,
                duration_minutes=doctor.slot_duration_minutes,
                status=AppointmentStatus.SCHEDULED.value,
                reason=reason,
                notes=notes
            )
            session.add(appointment)
            await session.commit()
            await session.refresh(appointment)

            return {
                "success": True,
                "appointment_id": appointment.id,
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
                "specialty": doctor.specialty,
                "datetime": appointment_datetime.isoformat(),
                "formatted_datetime": appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p"),
                "duration": f"{doctor.slot_duration_minutes} minutes",
                "fee": f"₹{doctor.consultation_fee}",
                "status": appointment.status
            }

    async def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancel an existing appointment"""
        async with async_session() as session:
            appointment = await session.get(Appointment, appointment_id)
            if not appointment:
                return {"success": False, "error": "Appointment not found"}

            appointment.status = AppointmentStatus.CANCELLED.value
            await session.commit()

            return {
                "success": True,
                "message": f"Appointment #{appointment_id} has been cancelled",
                "appointment_id": appointment_id
            }

    async def get_patient_appointments(self, patient_email: str) -> List[Dict]:
        """Get all appointments for a patient"""
        async with async_session() as session:
            result = await session.execute(
                select(Patient).where(Patient.email == patient_email)
            )
            patient = result.scalar_one_or_none()
            if not patient:
                return []

            result = await session.execute(
                select(Appointment, Doctor).join(
                    Doctor, Appointment.doctor_id == Doctor.id
                ).where(
                    and_(
                        Appointment.patient_id == patient.id,
                        Appointment.status.in_(["scheduled", "confirmed"])
                    )
                ).order_by(Appointment.appointment_date)
            )
            rows = result.all()

            return [
                {
                    "appointment_id": appt.id,
                    "doctor_name": f"Dr. {doc.first_name} {doc.last_name}",
                    "specialty": doc.specialty,
                    "date": appt.appointment_date.strftime("%A, %B %d, %Y"),
                    "time": appt.appointment_date.strftime("%I:%M %p"),
                    "reason": appt.reason,
                    "fee": f"₹{doc.consultation_fee}",
                    "status": appt.status
                }
                for appt, doc in rows
            ]

    async def get_doctors(self, specialty: Optional[str] = None) -> List[Dict]:
        """Get list of doctors"""
        async with async_session() as session:
            query = select(Doctor).where(Doctor.is_active == True)
            if specialty:
                query = query.where(Doctor.specialty.ilike(f"%{specialty}%"))

            result = await session.execute(query)
            doctors = result.scalars().all()

            return [
                {
                    "id": doc.id,
                    "name": f"Dr. {doc.first_name} {doc.last_name}",
                    "specialty": doc.specialty,
                    "qualification": doc.qualification,
                    "bio": doc.bio,
                    "available_days": doc.available_days,
                    "slot_duration": f"{doc.slot_duration_minutes} minutes",
                    "fee": f"₹{doc.consultation_fee}"
                }
                for doc in doctors
            ]

    async def _find_or_create_patient(
        self,
        session: AsyncSession,
        patient_info: Dict
    ) -> Patient:
        """Find existing patient or create new one"""
        email = patient_info.get("email")

        if email:
            result = await session.execute(
                select(Patient).where(Patient.email == email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                if "phone" in patient_info:
                    existing.phone = patient_info["phone"]
                if "insurance_id" in patient_info:
                    existing.insurance_id = patient_info["insurance_id"]
                await session.commit()
                return existing

        patient = Patient(
            first_name=patient_info.get("first_name", "Unknown"),
            last_name=patient_info.get("last_name", "Patient"),
            email=email or f"patient_{datetime.now().timestamp()}@temp.com",
            phone=patient_info.get("phone", "N/A"),
            date_of_birth=patient_info.get("date_of_birth", "N/A"),
            insurance_id=patient_info.get("insurance_id"),
            insurance_provider=patient_info.get("insurance_provider")
        )
        session.add(patient)
        await session.commit()
        await session.refresh(patient)
        return patient
