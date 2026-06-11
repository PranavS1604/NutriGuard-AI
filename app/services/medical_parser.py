import os
import re
import json
from typing import Dict, Any, Optional

try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel

    class MedicalProfile(BaseModel):
        conditions: list[str]
        allergies: list[str]
        medications: list[str]
        risk_level: str

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    MedicalProfile = None


# ── Regex fallback patterns ────────────────────────────────────────────────

_CONDITIONS = {
    r"\bDIABETES(?:\s+MELLITUS)?\b": "Diabetes",
    r"\bHYPERTENSION\b": "Hypertension",
    r"\bHIGH\s+BLOOD\s+PRESSURE\b": "Hypertension",
    r"\bHYPERLIPIDEMIA\b": "High Cholesterol",
    r"\bHIGH\s+CHOLESTEROL\b": "High Cholesterol",
    r"\bCHOLESTEROL\b": "High Cholesterol",
    r"\bTHYROID\b": "Thyroid Disorder",
    r"\bHYPOTHYROIDISM\b": "Hypothyroidism",
    r"\bHYPERTHYROIDISM\b": "Hyperthyroidism",
    r"\bASTHMA\b": "Asthma",
    r"\bARTHRITIS\b": "Arthritis",
    r"\bHEART\s+DISEASE\b": "Heart Disease",
    r"\bCORONARY\s+ARTERY\b": "Coronary Artery Disease",
    r"\bKIDNEY\s+DISEASE\b": "Kidney Disease",
    r"\bLIVER\s+DISEASE\b": "Liver Disease",
    r"\bANEMIA\b": "Anemia",
    r"\bGERD\b": "GERD",
    r"\bACID\s+REFLUX\b": "GERD",
    r"\bMIGRAINE\b": "Migraine",
    r"\bEPILEPSY\b": "Epilepsy",
    r"\bDEPRESSION\b": "Depression",
    r"\bANXIETY\b": "Anxiety",
    r"\bPARKINSON\b": "Parkinson's Disease",
    r"\bALZHEIMER\b": "Alzheimer's Disease",
}

_ALLERGIES = {
    r"\bPEANUT(?:S)?\b": "Peanuts",
    r"\bTREE\s+NUT(?:S)?\b": "Tree Nuts",
    r"\bWALNUT(?:S)?\b": "Tree Nuts",
    r"\bCASHEW(?:S)?\b": "Tree Nuts",
    r"\bALMOND(?:S)?\b": "Tree Nuts",
    r"\bMILK\b": "Dairy/Milk",
    r"\bDIARY\b": "Dairy/Milk",
    r"\bDARY\b": "Dairy/Milk",
    r"\bLACTOSE\b": "Dairy/Milk",
    r"\bSHELLFISH\b": "Shellfish",
    r"\bSHRIMP\b": "Shellfish",
    r"\bPRAWN(?:S)?\b": "Shellfish",
    r"\bLOBSTER\b": "Shellfish",
    r"\bCRAB\b": "Shellfish",
    r"\bFISH\s+ALLERG": "Fish",
    r"\bSESAME\b": "Sesame",
    r"\bGLUTEN\b": "Gluten",
    r"\bWHEAT\s+ALLERG": "Gluten/Wheat",
    r"\bCELIAC\b": "Gluten/Wheat",
    r"\bEGG\s+ALLERG": "Eggs",
    r"\bSOY\s+ALLERG": "Soy",
    r"\bPENICILLIN\b": "Penicillin (Drug)",
    r"\bSULFA\b": "Sulfa (Drug)",
    r"\bNSAID\b": "NSAIDs (Drug)",
    r"\bASPIRIN\s+ALLERG": "Aspirin (Drug)",
}

_MEDICATIONS = {
    r"\bWARFARIN\b": "Warfarin",
    r"\bCOUMADIN\b": "Warfarin",
    r"\bATORVASTATIN\b": "Atorvastatin",
    r"\bLIPITOR\b": "Atorvastatin",
    r"\bROSUVASTATIN\b": "Rosuvastatin",
    r"\bCRESTOR\b": "Rosuvastatin",
    r"\bSIMVASTATIN\b": "Simvastatin",
    r"\bMETFORMIN\b": "Metformin",
    r"\bGLUCOPHAGE\b": "Metformin",
    r"\bINSULIN\b": "Insulin",
    r"\bLEVOTHYROXINE\b": "Levothyroxine",
    r"\bSYNTHROID\b": "Levothyroxine",
    r"\bOMEPRAZOLE\b": "Omeprazole",
    r"\bPRILOSEC\b": "Omeprazole",
    r"\bAMLODIPINE\b": "Amlodipine",
    r"\bNORVASC\b": "Amlodipine",
    r"\bLISINOPRIL\b": "Lisinopril",
    r"\bMETOPROLOL\b": "Metoprolol",
    r"\bASPIRIN\b": "Aspirin",
    r"\bCLOPIDOGREL\b": "Clopidogrel",
    r"\bPLAVIX\b": "Clopidogrel",
    r"\bCYCLOSPORINE\b": "Cyclosporine",
    r"\bSTATIN(?:S)?\b": "Statins",
    r"\bMAO\s+INHIBITOR": "MAO Inhibitors",
    r"\bMAOI\b": "MAO Inhibitors",
    r"\bPHENELZINE\b": "MAO Inhibitors",
    r"\bTRANYLCYPROMINE\b": "MAO Inhibitors",
    r"\bPREDNISONE\b": "Prednisone",
    r"\bDIGOXIN\b": "Digoxin",
    r"\bFURO?SEMIDE\b": "Furosemide",
    r"\bLASIX\b": "Furosemide",
    r"\bGABAPENTIN\b": "Gabapentin",
    r"\bSERTRALINE\b": "Sertraline",
    r"\bZOLOFT\b": "Sertraline",
    r"\bFLUOXETINE\b": "Fluoxetine",
    r"\bPROZAC\b": "Fluoxetine",
    r"\bALLOPURINOL\b": "Allopurinol",
    r"\bHYDROXYCHLOROQUINE\b": "Hydroxychloroquine",
}


def _parse_fallback(text: str) -> Dict[str, Any]:
    upper = text.upper()

    conditions = list({v for p, v in _CONDITIONS.items() if re.search(p, upper)})
    allergies = list({v for p, v in _ALLERGIES.items() if re.search(p, upper)})
    medications = list({v for p, v in _MEDICATIONS.items() if re.search(p, upper)})

    risk_level = "Low"
    high_risk_meds = {"warfarin", "cyclosporine", "digoxin", "mao inhibitors"}
    high_risk_allergies = {"peanuts", "shellfish", "tree nuts"}
    
    if any(m.lower() in high_risk_meds for m in medications):
        risk_level = "High"
    elif any(a.lower() in high_risk_allergies for a in allergies):
        risk_level = "High"
    elif conditions or medications or allergies:
        risk_level = "Moderate"

    return {
        "conditions": conditions,
        "allergies": allergies,
        "medications": medications,
        "risk_level": risk_level,
    }


def parse_medical_text(text: str) -> Dict[str, Any]:
    """
    Parse medical text to extract conditions, allergies, medications.
    Uses Gemini LLM when available; falls back to regex patterns.
    """
    stripped = text.strip()
    if not stripped:
        return {"conditions": [], "allergies": [], "medications": [], "risk_level": "Low"}

    # Use Gemini for any non-trivial text
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # FIX: Lowered character threshold to 15 so it catches short inputs like "I take Warfarin"
    if api_key and _GENAI_AVAILABLE and len(stripped) >= 15:
        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                "You are a medical data extraction assistant. Extract structured medical information "
                "from the following text. Be thorough — the text may be informal, abbreviated, or OCR output.\n\n"
                f"Text:\n{stripped}\n\n"
                "Extract all conditions/diseases, allergies (food and drug), and active medications. "
                "Assess risk_level as 'Low', 'Moderate', or 'High' based on the severity of conditions "
                "and medications found. High = critical drugs (Warfarin, Cyclosporine, MAOIs) or "
                "life-threatening allergies (anaphylaxis, severe). Moderate = any chronic condition or medication. "
                "Return only JSON."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MedicalProfile,
                    temperature=0.1,
                ),
            )
            if response.text:
                data = json.loads(response.text)
                # Ensure all keys exist
                return {
                    "conditions": data.get("conditions", []),
                    "allergies": data.get("allergies", []),
                    "medications": data.get("medications", []),
                    "risk_level": data.get("risk_level", "Low"),
                }
        except Exception as e:
            print(f"[MedicalParser] Gemini failed: {e}. Using regex fallback.")

    return _parse_fallback(stripped)