import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import streamlit as st

# =====================================================================
# 1. PAGE CONFIG & MODERN CLINICAL STYLESHEET
# =====================================================================
st.set_page_config(
    page_title="MedTriage Pro | AI Clinical Support",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #F8FAFC;
    }

    /* Header Container */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 60%, #0284C7 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: #FFFFFF;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF;
    }
    .hero-sub {
        font-size: 0.95rem;
        color: #38BDF8;
        margin-top: 4px;
    }

    /* Red Flag Emergency Box */
    .emergency-box {
        background-color: #FEF2F2;
        border: 2px solid #EF4444;
        border-left: 8px solid #DC2626;
        border-radius: 12px;
        padding: 20px;
        color: #991B1B;
        margin-bottom: 20px;
    }

    /* ESI Dynamic Banner */
    .esi-banner {
        padding: 18px 24px;
        border-radius: 14px;
        color: white;
        font-weight: 700;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .esi-1 { background: linear-gradient(135deg, #DC2626, #991B1B); }
    .esi-2 { background: linear-gradient(135deg, #EA580C, #C2410C); }
    .esi-3 { background: linear-gradient(135deg, #D97706, #B45309); }
    .esi-4 { background: linear-gradient(135deg, #0284C7, #0369A1); }
    .esi-5 { background: linear-gradient(135deg, #059669, #047857); }

    /* Vitals Status Badges */
    .vital-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-left: 6px;
    }
    .vital-normal { background: #DCFCE7; color: #166534; }
    .vital-alert { background: #FEE2E2; color: #991B1B; }

    /* Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-label { font-size: 0.75rem; color: #64748B; font-weight: 700; text-transform: uppercase; }
    .metric-val { font-size: 1.25rem; color: #0F172A; font-weight: 800; margin-top: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================================
# 2. SESSION STATE MANAGEMENT & PRESET CALLBACKS
# =====================================================================
defaults = {
    "complaint_key": "",
    "severity_key": 4,
    "hr_key": 72,
    "bp_key": "120/80",
    "temp_key": 98.6,
    "spo2_key": 98,
    "duration_key": "24–48 Hours",
    "notes_key": "",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def set_preset(complaint, severity, hr, bp, temp, spo2, duration, notes=""):
    st.session_state["complaint_key"] = complaint
    st.session_state["severity_key"] = severity
    st.session_state["hr_key"] = hr
    st.session_state["bp_key"] = bp
    st.session_state["temp_key"] = temp
    st.session_state["spo2_key"] = spo2
    st.session_state["duration_key"] = duration
    st.session_state["notes_key"] = notes


# =====================================================================
# 3. TIER 1: DETERMINISTIC EMERGENCY GUARDRAILS
# =====================================================================
RED_FLAG_PATTERNS = [
    r"chest pain", r"shortness of breath", r"difficulty breathing",
    r"severe bleeding", r"fainted", r"unconscious", r"stroke",
    r"numbness on one side", r"slurred speech", r"sudden loss of vision",
    r"coughing blood", r"anaphylaxis", r"swelling of tongue",
    r"crushing chest", r"worst headache of life"
]


def check_tier1_emergency(user_input: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    clean_input = user_input.lower()
    matched = [p for p in RED_FLAG_PATTERNS if re.search(p, clean_input)]
    if matched:
        return True, {
            "is_emergency": True,
            "tier": "TIER_1_DETERMINISTIC_GUARDRAIL",
            "action": "IMMEDIATE_ER_REDIRECT",
            "esi_level": 1,
            "category": "Life-Threatening Emergency",
            "matched_triggers": matched,
            "message": "CRITICAL WARNING: Symptoms indicate a high risk of a medical emergency. Call 911 / 119 or go to the nearest ER immediately.",
            "timestamp": datetime.utcnow().isoformat(),
        }
    return False, None


# =====================================================================
# 4. TIER 2: ADAPTIVE CLINICAL TRIAGE ENGINE
# =====================================================================
SPECIALIST_MAPPING = {
    "joint": "Orthopedics", "knee": "Orthopedics", "fracture": "Orthopedics", "bone": "Orthopedics",
    "skin": "Dermatology", "rash": "Dermatology", "stomach": "Gastroenterology", "abdominal": "Gastroenterology",
    "headache": "Neurology", "migraine": "Neurology", "fever": "General Internal Medicine",
    "cough": "Pulmonology", "eye": "Ophthalmology", "vision": "Ophthalmology"
}


class ClinicalTriageEngine:
    def __init__(self, api_key: Optional[str] = None, provider: str = "Offline Rule Engine"):
        self.api_key = api_key
        self.provider = provider

    def evaluate(self, complaint: str, duration: str, severity: int, hr: int, bp: str, temp: float, spo2: int, notes: str) -> Dict[str, Any]:
        context = f"Complaint: {complaint}. Duration: {duration}. Pain: {severity}/10. Vitals: HR={hr}bpm, BP={bp}, Temp={temp}°F, SpO2={spo2}%. Notes: {notes}"

        if self.api_key and self.provider == "Google Gemini API":
            try:
                return self._gemini_inference(context)
            except Exception as err:
                st.sidebar.error(f"Gemini API Error ({err}). Fallback activated.")

        return self._heuristic_fallback(complaint, duration, severity, hr, temp, spo2, notes)

    def _heuristic_fallback(self, complaint: str, duration: str, severity: int, hr: int, temp: float, spo2: int, notes: str) -> Dict[str, Any]:
        text = f"{complaint} {notes}".lower()

        if severity >= 8 or temp >= 102.5 or hr >= 120 or spo2 < 92 or "severe" in text:
            esi = 2
            urgency = "Emergent (High Risk)"
            timeframe = "Within 15–30 Minutes"
        elif severity >= 5 or temp >= 100.5 or "swelling" in text or "moderate" in text:
            esi = 3
            urgency = "Urgent Care"
            timeframe = "Within 2–4 Hours"
        elif severity >= 3:
            esi = 4
            urgency = "Less Urgent"
            timeframe = "Within 24 Hours"
        else:
            esi = 5
            urgency = "Non-Urgent Routine"
            timeframe = "Scheduled Appointment"

        specialty = "General Internal Medicine"
        for kw, dept in SPECIALIST_MAPPING.items():
            if kw in text:
                specialty = dept
                break

        return {
            "is_emergency": False,
            "tier": "TIER_2_HEURISTIC_CLINICAL_ENGINE",
            "esi_level": esi,
            "urgency_label": urgency,
            "recommended_specialty": specialty,
            "recommended_timeframe": timeframe,
            "clinical_reasoning": f"Assessed chief complaint with Pain Score {severity}/10, Temperature {temp}°F, and SpO2 {spo2}%. Symptom pattern correlates with ESI Level {esi}.",
            "follow_up_questions": [
                "Does the discomfort radiate or worsen with physical movement?",
                "Are you currently taking any prescription medications?",
                "Do you have a history of similar symptoms?"
            ],
            "action_plan": [
                f"Refer to {specialty} for clinical assessment.",
                "Re-check vitals every 2 hours if waiting.",
                "Escalate immediately if severe shortness of breath or chest pain occurs."
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _gemini_inference(self, context: str) -> Dict[str, Any]:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        Act as an expert clinical emergency triage AI. Analyze this case context and output ONLY valid JSON:
        Context: {context}

        JSON Schema:
        {{
            "is_emergency": false,
            "tier": "TIER_2_GEMINI_AI_MODEL",
            "esi_level": <integer 2 to 5>,
            "urgency_label": "<short string>",
            "recommended_specialty": "<department>",
            "recommended_timeframe": "<timeframe>",
            "clinical_reasoning": "<concise explanation>",
            "follow_up_questions": ["<q1>", "<q2>"],
            "action_plan": ["<act1>", "<act2>"]
        }}
        """
        response = model.generate_content(prompt)
        clean = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)


# =====================================================================
# 5. STREAMLIT DASHBOARD INTERFACE
# =====================================================================
def main():
    # Hero Header Banner
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-title">🩺 MedTriage Pro AI</div>
            <div class="hero-sub">Clinical Decision Support System & Emergency Severity Index (ESI) Engine</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar Controls
    with st.sidebar:
        st.markdown("### ⚙️ Engine Settings")
        provider = st.radio(
            "Select Triage Model Engine:",
            ["Offline Rule Engine", "Google Gemini API"],
            help="Choose between local safety engine or Google Gemini API."
        )

        api_key = None
        if provider == "Google Gemini API":
            api_key = st.text_input("Gemini API Key:", type="password")

        st.divider()
        st.markdown("### 📊 ESI Reference Matrix")
        st.markdown("""
        - **ESI 1**: Resuscitation (Immediate)
        - **ESI 2**: Emergent (High Risk)
        - **ESI 3**: Urgent (2+ Resources)
        - **ESI 4**: Less Urgent (1 Resource)
        - **ESI 5**: Non-Urgent (0 Resources)
        """)

    # Quick Preset Buttons Row
    st.markdown("##### ⚡ Quick Clinical Scenario Presets (Click to Load)")
    p1, p2, p3, p4, p5 = st.columns(5)

    p1.button("🚨 Chest Pain", use_container_width=True, on_click=set_preset, args=("Sudden crushing chest pain and severe shortness of breath.", 9, 118, "148/92", 98.6, 94, "Under 12 Hours"))
    p2.button("🦴 Knee Joint", use_container_width=True, on_click=set_preset, args=("Right knee joint pain and moderate swelling after running.", 6, 80, "122/80", 98.8, 98, "24–48 Hours"))
    p3.button("🩹 Skin Rash", use_container_width=True, on_click=set_preset, args=("Itchy red skin rash across both arms for three days.", 3, 72, "118/75", 98.4, 99, "3–7 Days"))
    p4.button("🤢 Stomach Pain", use_container_width=True, on_click=set_preset, args=("Abdominal crampy pain accompanied by nausea after eating.", 5, 86, "126/82", 99.4, 97, "24–48 Hours"))
    p5.button("👁️ Vision / Head", use_container_width=True, on_click=set_preset, args=("Dull migraine headache with blurry vision when reading.", 4, 75, "120/78", 98.6, 98, "Over 1 Week"))

    st.markdown("<br/>", unsafe_allow_html=True)

    # Main Grid Layout
    col_input, col_output = st.columns([1.1, 0.9], gap="large")

    with col_input:
        st.markdown("### 📋 Patient Intake & Vitals")

        with st.form("intake_form"):
            symptom_in = st.text_area(
                "Chief Medical Complaint / Symptoms *",
                key="complaint_key",
                placeholder="Describe patient symptoms in detail...",
                height=110,
            )

            st.markdown("##### 🩺 Patient Vitals Entry")
            v1, v2, v3, v4 = st.columns(4)
            with v1:
                hr_in = st.number_input("Heart Rate (BPM)", 40, 200, key="hr_key")
            with v2:
                bp_in = st.text_input("BP (mmHg)", key="bp_key")
            with v3:
                temp_in = st.number_input("Temp (°F)", 94.0, 106.0, step=0.1, key="temp_key")
            with v4:
                spo2_in = st.number_input("SpO2 (%)", 70, 100, key="spo2_key")

            d1, d2 = st.columns(2)
            with d1:
                duration_in = st.selectbox("Symptom Duration", ["Under 12 Hours", "24–48 Hours", "3–7 Days", "Over 1 Week"], key="duration_key")
            with d2:
                severity_in = st.slider("Pain Severity (1–10)", 1, 10, key="severity_key")

            notes_in = st.text_input("Medical History / Notes", key="notes_key", placeholder="e.g., Asthma, Hypertension, Allergies")

            submitted = st.form_submit_button("🚀 Run Clinical Triage Engine", use_container_width=True)

    with col_output:
        st.markdown("### 📊 Triage Analysis & Decision Support")

        if submitted and symptom_in:
            # 1. Tier 1 Safety Check
            is_emergency, em_payload = check_tier1_emergency(symptom_in)

            if is_emergency:
                st.markdown(
                    f"""
                    <div class="emergency-box">
                        <div style="font-size: 1.3rem; font-weight: 800; color: #DC2626;">🚨 TIER-1 EMERGENCY RED FLAG DETECTED</div>
                        <p style="margin-top: 8px;"><strong>Matched Triggers:</strong> {', '.join(em_payload['matched_triggers'])}</p>
                        <p style="font-size: 1.05rem; font-weight: 600;">{em_payload['message']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.error("🚨 REDIRECT MANDATE: Patient must be immediately directed to Emergency Care or 911.")
                with st.expander("📄 View Safety Intercept JSON"):
                    st.json(em_payload)

            else:
                # 2. Tier 2 AI Assessment
                triage_engine = ClinicalTriageEngine(api_key=api_key, provider=provider)

                with st.spinner("Evaluating clinical indicators & mapping specialty..."):
                    res = triage_engine.evaluate(symptom_in, duration_in, severity_in, hr_in, bp_in, temp_in, spo2_in, notes_in)

                esi = res.get("esi_level", 3)

                # Visual ESI Hero Banner
                st.markdown(
                    f"""
                    <div class="esi-banner esi-{esi}">
                        <div>
                            <div style="font-size: 0.8rem; text-transform: uppercase; opacity: 0.9;">Emergency Severity Index</div>
                            <div style="font-size: 1.8rem; font-weight: 800;">ESI LEVEL {esi}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.1rem; font-weight: 700;">{res.get('urgency_label')}</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">Target: {res.get('recommended_timeframe')}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # KPI Display Grid
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Specialty</div><div class="metric-val" style="color:#0284C7;">{res.get("recommended_specialty")}</div></div>', unsafe_allow_html=True)
                with k2:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Timeframe</div><div class="metric-val" style="color:#D97706;">{res.get("recommended_timeframe")}</div></div>', unsafe_allow_html=True)
                with k3:
                    st.markdown(f'<div class="metric-card"><div class="metric-label">Pain Score</div><div class="metric-val" style="color:#DC2626;">{severity_in} / 10</div></div>', unsafe_allow_html=True)

                st.markdown("<br/>", unsafe_allow_html=True)

                # Tabbed Detailed Results
                t_plan, t_reason, t_ehr = st.tabs(["📋 Clinical Care Plan", "🧠 AI Reasoning", "📄 EHR JSON Payload"])

                with t_plan:
                    st.markdown("#### Recommended Clinical Steps")
                    for act in res.get("action_plan", []):
                        st.write(f"• **{act}**")

                    st.markdown("---")
                    st.markdown("#### Follow-up Clarification Questions")
                    for q in res.get("follow_up_questions", []):
                        st.write(f"❓ *{q}*")

                with t_reason:
                    st.info(res.get("clinical_reasoning"))
                    st.write(f"**Tier Engine:** `{res.get('tier')}`")
                    st.write(f"**Timestamp:** `{res.get('timestamp')}`")

                with t_ehr:
                    st.json(res)
                    st.download_button(
                        label="📥 Download Structured EHR JSON",
                        data=json.dumps(res, indent=2),
                        file_name=f"triage_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                    )

        elif submitted and not symptom_in:
            st.warning("Please enter patient symptoms before evaluating.")
        else:
            st.info("👈 Enter patient symptoms or click one of the quick preset scenario buttons above.")


if __name__ == "__main__":
    main()
