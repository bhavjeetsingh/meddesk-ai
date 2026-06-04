"""
CareFirst Medical Center - Clinic Tools
Directory lookup, billing info, insurance verification, directions (Indian Context)
"""
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class ClinicTools:
    """Collection of tools for the AI receptionist (Indian Context)"""

    def __init__(self, config):
        self.config = config
        self._build_knowledge_base()

    def _build_knowledge_base(self):
        """Build internal knowledge base for quick lookups"""
        self.clinic_info = {
            "name": self.config.clinic_name,
            "phone": self.config.clinic_phone,
            "email": self.config.clinic_email,
            "address": self.config.clinic_address,
            "hours": self.config.clinic_hours,
            "website": "www.carefirstmedical.in",
            "parking": "Free parking available in the building basement. Valet parking available on weekdays.",
            "wifi": "Free WiFi available. Network: CareFirst-Guest, Password: Welcome2024"
        }

        self.services = {
            "general_consultation": {
                "name": "General Consultation",
                "description": "Comprehensive health examination, preventive care, chronic disease management",
                "duration": "30 minutes",
                "cost": "₹1,000"
            },
            "cardiology": {
                "name": "Cardiology Consultation",
                "description": "Heart health assessment, ECG, echo, stress tests",
                "duration": "45 minutes",
                "cost": "₹1,500"
            },
            "ecg": {
                "name": "ECG (Electrocardiogram)",
                "description": "Heart rhythm test, 12-lead ECG with report",
                "duration": "15 minutes",
                "cost": "₹500"
            },
            "echocardiography": {
                "name": "Echocardiography",
                "description": "Ultrasound of the heart, detailed cardiac assessment",
                "duration": "30 minutes",
                "cost": "₹3,000"
            },
            "blood_work": {
                "name": "Blood Tests",
                "description": "Complete blood count, sugar, lipid profile, thyroid",
                "duration": "15 minutes",
                "cost": "₹300 - ₹2,000"
            },
            "diabetes_management": {
                "name": "Diabetes Management",
                "description": "HbA1c testing, sugar monitoring, insulin management",
                "duration": "30 minutes",
                "cost": "₹1,200"
            },
            "vaccination": {
                "name": "Vaccination",
                "description": "Flu shots, hepatitis, tetanus, COVID vaccines",
                "duration": "15 minutes",
                "cost": "₹100 - ₹2,500"
            },
            "health_checkup": {
                "name": "Complete Health Checkup",
                "description": "Full body checkup with blood tests, ECG, and doctor consultation",
                "duration": "2 hours",
                "cost": "₹3,500"
            },
            "teleconsultation": {
                "name": "Teleconsultation",
                "description": "Video consultation with doctor from home",
                "duration": "20 minutes",
                "cost": "₹800"
            }
        }

        self.insurance_providers = [
            "Star Health & Allied Insurance",
            "ICICI Lombard",
            "Bajaj Allianz",
            "HDFC ERGO",
            "New India Assurance",
            "Oriental Insurance",
            "United India Insurance",
            "Care Health Insurance (Religare)",
            "Niva Bupa",
            "Aditya Birla Health Insurance",
            "ManipalCigna",
            "Tata AIG",
            "Go Digit",
            "Digit Insurance"
        ]

        self.government_schemes = [
            "Ayushman Bharat (PMJAY)",
            "CGHS (Central Government Health Scheme)",
            "ECHS (Ex-Servicemen Contributory Health Scheme)",
            "Mahatma Jyotiba Phule Jan Arogya Yojana (Maharashtra)",
            "Rashtriya Swasthya Bima Yojana"
        ]

        self.policies = {
            "cancellation": "We require 24-hour notice for cancellations. Late cancellations may incur a ₹500 fee.",
            "no_show": "No-shows may result in a ₹1,000 fee and possible discharge from the practice after 3 occurrences.",
            "payment": "We accept cash, UPI (Google Pay, PhonePe, Paytm), credit/debit cards, and net banking. Payment is due at time of service.",
            "insurance": "We offer cashless treatment for most major insurance providers. Please bring your insurance card and photo ID.",
            "prescription": "Prescription refills require 48-hour notice. Please contact your pharmacy first.",
            "records": "Medical records requests take 5-7 business days to process. A ₹200 administrative fee may apply.",
            "teleconsultation": "Teleconsultation available for follow-ups and non-urgent consultations. ₹800 flat fee.",
            "gst": "GST of 18% is applicable on consultation fees as per government norms.",
            "abha": "We support ABHA (Ayushman Bharat Health Account) for digital health records."
        }

        self.emergency_info = {
            "message": "For medical emergencies, please call 108 (Ambulance) or 102 immediately.",
            "clinic_emergency": "For clinic-related urgent queries, call: +91 98765 43210",
            "nearby_hospitals": [
                "Breach Candy Hospital - 2 km",
                "Jaslok Hospital - 3 km",
                "Kokilaben Dhirubhai Ambani Hospital - 5 km"
            ],
            "blood_bank": "Blood Bank: +91 22 2496 6111 (Indian Red Cross Society)",
            "poison_control": "Poison Control: 1066"
        }

    def get_clinic_info(self, topic: Optional[str] = None) -> str:
        """Get clinic information"""
        if topic and topic.lower() in self.clinic_info:
            return f"{topic.title()}: {self.clinic_info[topic.lower()]}"
        return "\n".join([f"{k.title()}: {v}" for k, v in self.clinic_info.items()])

    def get_service_info(self, service_type: Optional[str] = None) -> str:
        """Get service information"""
        if service_type:
            for key, service in self.services.items():
                if service_type.lower() in key or service_type.lower() in service["name"].lower():
                    return (
                        f"{service['name']}\n"
                        f"Description: {service['description']}\n"
                        f"Duration: {service['duration']}\n"
                        f"Cost: {service['cost']}"
                    )
            return f"Service '{service_type}' not found. Available: {', '.join(s['name'] for s in self.services.values())}"

        result = "Available Services:\n\n"
        for key, service in self.services.items():
            result += f"• {service['name']}: {service['description']} ({service['cost']})\n"
        return result

    def check_insurance(self, provider: str) -> str:
        """Check if insurance provider is accepted"""
        for p in self.insurance_providers:
            if provider.lower() in p.lower():
                return (
                    f"✅ Yes! We accept {p}.\n\n"
                    f"Cashless treatment is available. Please bring:\n"
                    f"• Insurance card\n"
                    f"• Photo ID (Aadhaar/ PAN/ Passport)\n"
                    f"• Pre-authorization (if required)\n\n"
                    f"For queries, call our insurance desk: +91 98765 43210"
                )

        for s in self.government_schemes:
            if provider.lower() in s.lower():
                return (
                    f"✅ Yes! We accept {s}.\n\n"
                    f"Please bring your scheme card and valid ID proof."
                )

        return (
            f"We don't have {provider} in our cashless network. "
            f"However, you can avail reimbursement by paying upfront and claiming from your insurer.\n\n"
            f"Accepted providers: {', '.join(self.insurance_providers[:5])}..."
        )

    def get_policies(self, policy_type: Optional[str] = None) -> str:
        """Get clinic policies"""
        if policy_type:
            for key, policy in self.policies.items():
                if policy_type.lower() in key:
                    return f"{key.title()} Policy: {policy}"
            return f"Policy '{policy_type}' not found."

        result = "Clinic Policies:\n\n"
        for key, policy in self.policies.items():
            result += f"• {key.title()}: {policy}\n"
        return result

    def get_directions(self) -> str:
        """Get directions to the clinic"""
        return (
            f"We are located at {self.config.clinic_address}.\n\n"
            f"By Metro:\n"
            f"• Andheri Metro Station (East) - 5 min auto ride\n"
            f"• Walk straight on MG Road, Sunshine Plaza is on the left\n\n"
            f"By Bus:\n"
            f"• Bus routes 285, 295, 332 stop at MG Road Bus Stop\n\n"
            f"By Car:\n"
            f"• Free parking in building basement\n"
            f"• Valet parking available on weekdays\n\n"
            f"By Auto/Cab:\n"
            f"• Tell driver: 'Sunshine Plaza, MG Road, Andheri West'\n"
            f"• Landmark: Near Andheri Signal, next to McDonald's"
        )

    def get_emergency_info(self) -> str:
        """Get emergency information"""
        hospitals = "\n".join([f"  • {h}" for h in self.emergency_info["nearby_hospitals"]])
        return (
            f"🚨 {self.emergency_info['message']}\n\n"
            f"Clinic Urgent Queries: {self.emergency_info['clinic_emergency']}\n\n"
            f"Nearby Hospitals:\n{hospitals}\n\n"
            f"Blood Bank: {self.emergency_info['blood_bank']}\n"
            f"Poison Control: {self.emergency_info['poison_control']}"
        )

    def get_wait_times(self) -> Dict:
        """Get estimated wait times (simulated for demo)"""
        now = datetime.now()
        hour = now.hour

        if 9 <= hour < 11:
            base_wait = 10
        elif 11 <= hour < 14:
            base_wait = 25
        elif 14 <= hour < 17:
            base_wait = 15
        elif 17 <= hour < 20:
            base_wait = 20
        else:
            base_wait = 5

        return {
            "general_practice": f"{base_wait} minutes",
            "cardiology": f"{base_wait + 10} minutes",
            "last_updated": now.strftime("%I:%M %p")
        }

    def format_response(self, intent: str, data: any) -> str:
        """Format tool responses for natural conversation"""
        if intent == "clinic_info":
            return self.get_clinic_info(str(data))
        elif intent == "services":
            return self.get_service_info(str(data) if data else None)
        elif intent == "insurance":
            return self.check_insurance(str(data))
        elif intent == "policies":
            return self.get_policies(str(data) if data else None)
        elif intent == "directions":
            return self.get_directions()
        elif intent == "emergency":
            return self.get_emergency_info()
        elif intent == "wait_times":
            waits = self.get_wait_times()
            return "Current estimated wait times:\n" + "\n".join(
                [f"• {k.replace('_', ' ').title()}: {v}" for k, v in waits.items() if k != "last_updated"]
            )
        return "I can help you with clinic information, services, insurance, and more."
