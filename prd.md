# MedTriage Pro

## Original problem statement
Convert the supplied Streamlit MedTriage Pro clinical decision-support prototype into a polished, working app with deterministic emergency guardrails, ESI triage, vitals intake, quick presets, specialty/timeframe recommendations, care plan, follow-up questions, and structured EHR JSON download.

## Architecture decisions
- React frontend with a FastAPI `/api/triage` endpoint.
- Offline deterministic rule engine is the default so emergency safety checks do not depend on an external model.
- No persistence: each assessment remains session-based and the EHR payload is downloaded locally.
- Dark clinical dashboard UI with responsive mobile navigation and explicit decision-support disclaimer.

## Implemented
- Tier 1 red-flag detection for emergency symptoms with immediate redirect messaging.
- Tier 2 ESI 1–5 heuristic assessment using complaint, pain, temperature, heart rate, oxygen saturation, and notes.
- Quick scenario presets for chest pain, knee joint, skin rash, and stomach pain.
- Responsive patient intake form, live assessment output, care plan, follow-up questions, and EHR JSON download.
- Backend and frontend flows verified with routine and emergency cases.

## Prioritized backlog
- P0: Keep the emergency red-flag vocabulary reviewed by qualified clinical stakeholders.
- P1: Add clinician-authenticated case history and audit trail if persistent records are required.
- P1: Add configurable local emergency numbers and organization-specific escalation policies.
- P2: Add optional external clinical model integration behind explicit clinician consent and key management.
