from fastapi import FastAPI, APIRouter
from typing import List, Optional, Dict, Any
api_router = APIRouter(prefix="/api")

RED_FLAG_PATTERNS = [
    r"chest pain", r"shortness of breath", r"difficulty breathing",
    r"severe bleeding", r"fainted", r"unconscious", r"stroke",
    r"numbness on one side", r"slurred speech", r"sudden loss of vision",
    r"coughing blood", r"anaphylaxis", r"swelling of tongue",
    r"crushing chest", r"worst headache of life",
]

SPECIALIST_MAPPING = {
    "joint": "Orthopedics", "knee": "Orthopedics", "fracture": "Orthopedics", "bone": "Orthopedics",
    "skin": "Dermatology", "rash": "Dermatology", "stomach": "Gastroenterology", "abdominal": "Gastroenterology",
    "headache": "Neurology", "migraine": "Neurology", "fever": "General Internal Medicine",
    "cough": "Pulmonology", "eye": "Ophthalmology", "vision": "Ophthalmology",
}

class TriageRequest(BaseModel):
    complaint: str
    duration: str
    severity: int
    heart_rate: int
    blood_pressure: str
    temperature: float
    oxygen_saturation: int
    notes: str = ""

class TriageResponse(BaseModel):
    is_emergency: bool
    tier: str
    esi_level: int
    urgency_label: Optional[str] = None
    recommended_specialty: Optional[str] = None
    recommended_timeframe: Optional[str] = None
    clinical_reasoning: str
    follow_up_questions: List[str] = []
    action_plan: List[str] = []
    matched_triggers: List[str] = []
    message: Optional[str] = None
    timestamp: str
@api_router.get("/")
async def root():
    return {"message": "MedTriage Pro API online"}

@api_router.post("/triage", response_model=TriageResponse)
async def triage_case(payload: TriageRequest):
    import re
    now = datetime.now(timezone.utc).isoformat()
    text = f"{payload.complaint} {payload.notes}".lower()
    matched = [pattern for pattern in RED_FLAG_PATTERNS if re.search(pattern, text)]
    if matched:
        return TriageResponse(
            is_emergency=True,
            tier="TIER_1_DETERMINISTIC_GUARDRAIL",
            esi_level=1,
            clinical_reasoning="A red-flag symptom matched the emergency safety guardrail before any routine triage assessment.",
            matched_triggers=matched,
            message="Symptoms may indicate a medical emergency. Call your local emergency number or go to the nearest emergency department now.",
            timestamp=now,
        )

    if payload.severity >= 8 or payload.temperature >= 102.5 or payload.heart_rate >= 120 or payload.oxygen_saturation < 92 or "severe" in text:
        esi, urgency, timeframe = 2, "Emergent / high risk", "Within 15–30 minutes"
    elif payload.severity >= 5 or payload.temperature >= 100.5 or "swelling" in text or "moderate" in text:
        esi, urgency, timeframe = 3, "Urgent care", "Within 2–4 hours"
    elif payload.severity >= 3:
        esi, urgency, timeframe = 4, "Less urgent", "Within 24 hours"
    else:
        esi, urgency, timeframe = 5, "Non-urgent routine", "Schedule an appointment"

    specialty = "General Internal Medicine"
    for keyword, department in SPECIALIST_MAPPING.items():
        if keyword in text:
            specialty = department
            break

    return TriageResponse(
        is_emergency=False,
        tier="TIER_2_HEURISTIC_CLINICAL_ENGINE",
        esi_level=esi,
        urgency_label=urgency,
        recommended_specialty=specialty,
        recommended_timeframe=timeframe,
        clinical_reasoning=f"Pain score {payload.severity}/10, temperature {payload.temperature}°F, heart rate {payload.heart_rate} bpm, and SpO₂ {payload.oxygen_saturation}% map to ESI level {esi} under the offline safety rules.",
        follow_up_questions=["Does the discomfort radiate or worsen with movement?", "Are you taking any prescription medications?", "Have you had similar symptoms before?"],
        action_plan=[f"Refer to {specialty} for clinical assessment.", "Re-check vitals every 2 hours if waiting.", "Escalate immediately if severe breathing difficulty or chest pain occurs."],
        timestamp=now,
    )
