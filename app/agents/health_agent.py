from app.schemas.context import MissionContext
from app.schemas.health import HealthProfile
from app.tools.medical_ocr import perform_medical_ocr
from app.services.medical_parser import parse_medical_text

_HIGH_RISK_MEDS = {"warfarin", "cyclosporine", "digoxin", "mao inhibitors"}
_HIGH_RISK_ALLERGIES = {"peanuts", "shellfish", "tree nuts", "anaphylaxis"}

class HealthAgent:
    async def run(self, context: MissionContext) -> HealthProfile:
        conditions, allergies, medications = [], [], []

        for report_bytes in context.medical_reports:
            ocr_result = await perform_medical_ocr(report_bytes)
            text = ocr_result.extracted_text or ""
            if text and "Mocked OCR" not in text:
                parsed = parse_medical_text(text)
                conditions.extend(parsed.get("conditions", []))
                allergies.extend(parsed.get("allergies", []))
                medications.extend(parsed.get("medications", []))

        if not (conditions or allergies or medications):
            metadata = context.metadata or {}
            med_text = metadata.get("medical_text") or metadata.get("report_text") or ""
            if med_text and isinstance(med_text, str) and med_text.strip():
                parsed = parse_medical_text(med_text.strip())
                conditions.extend(parsed.get("conditions", []))
                allergies.extend(parsed.get("allergies", []))
                medications.extend(parsed.get("medications", []))

        conditions = list(dict.fromkeys(conditions))
        allergies = list(dict.fromkeys(allergies))
        medications = list(dict.fromkeys(medications))

        risk_level = "Low"
        meds_lower = {m.lower() for m in medications}
        allergies_lower = {a.lower() for a in allergies}

        if meds_lower & _HIGH_RISK_MEDS or allergies_lower & _HIGH_RISK_ALLERGIES:
            risk_level = "High"
        elif conditions or medications or allergies:
            risk_level = "Moderate"

        return HealthProfile(
            conditions=conditions, allergies=allergies, medications=medications, risk_level=risk_level,
        )