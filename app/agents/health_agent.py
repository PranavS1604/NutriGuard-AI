from app.schemas.context import MissionContext
from app.schemas.health import HealthProfile
from app.tools.medical_ocr import perform_medical_ocr
from app.services.medical_parser import parse_medical_text

class HealthAgent:
    async def run(self, context: MissionContext) -> HealthProfile:
        """
        Analyzes medical lab reports and prescriptions to build a structured health profile.
        If no medical data is provided, returns a clean empty profile (no fake hardcoded data).
        """
        ocr_results = []
        for report_bytes in context.medical_reports:
            ocr_result = await perform_medical_ocr(report_bytes)
            ocr_results.append(ocr_result.extracted_text)
        
        conditions = []
        allergies = []
        medications = []
        
        for text in ocr_results:
            parsed = parse_medical_text(text)
            conditions.extend(parsed["conditions"])
            allergies.extend(parsed["allergies"])
            medications.extend(parsed["medications"])
        
        # Also parse medical text from context metadata if provided directly
        if not conditions and not allergies and not medications:
            med_text = context.metadata.get("medical_text") or context.metadata.get("report_text")
            if med_text:
                parsed = parse_medical_text(med_text)
                conditions = parsed["conditions"]
                allergies = parsed["allergies"]
                medications = parsed["medications"]
            # No fallback to hardcoded data — return empty profile for real users
                
        conditions = list(set(conditions))
        allergies = list(set(allergies))
        medications = list(set(medications))
        
        # Calculate risk level dynamically based on actual data
        risk_level = "Low"
        if any(m.lower() in ["warfarin", "cyclosporine"] for m in medications):
            risk_level = "High"
        elif any(a.lower() in ["peanuts", "peanut", "shellfish", "tree nuts"] for a in allergies):
            risk_level = "High"
        elif conditions or medications or allergies:
            risk_level = "Moderate"
            
        return HealthProfile(
            conditions=conditions,
            allergies=allergies,
            medications=medications,
            risk_level=risk_level
        )

