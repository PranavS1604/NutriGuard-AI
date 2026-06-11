import os
import re
import json
from typing import Dict, Any

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

try:
    from sambanova import SambaNova
    _SAMBA_AVAILABLE = True
except ImportError:
    _SAMBA_AVAILABLE = False


def _regex_parser(text: str) -> Dict[str, Any]:
    text_upper = text.upper()
    conditions = []
    allergies = []
    medications = []

    CONDITION_MAP = {
        "Diabetes": [r"\bDIABETES\b", r"\bDIABETIC\b"],
        "Hypertension": [r"\bHYPERTENSION\b", r"\bHIGH BLOOD PRESSURE\b"],
        "High cholesterol": [r"\bCHOLESTEROL\b", r"\bHIGH CHOLESTEROL\b", r"\bHYPERLIPIDEMIA\b"]
    }

    ALLERGY_MAP = {
        "Peanuts": [r"\bPEANUT\b", r"\bPEANUTS\b", r"\bPEANUT ALLERGY\b"],
        "Milk": [r"\bMILK\b", r"\bLACTOSE\b"],
        "Shellfish": [r"\bSHELLFISH\b", r"\bSHRIMP\b", r"\bPRAWN\b", r"\bCRAB\b"],
        "Sesame": [r"\bSESAME\b"]
    }

    MEDICATION_MAP = {
        "Metformin": [r"\bMETFORMIN\b", r"\bGLUCOPHAGE\b"],
        "Warfarin": [r"\bWARFARIN\b", r"\bCOUMADIN\b"],
        "Atorvastatin": [r"\bATORVASTATIN\b", r"\bLIPITOR\b"],
        "Statins": [r"\bSTATIN\b", r"\bSTATINS\b"]
    }

    for label, patterns in CONDITION_MAP.items():
        if any(re.search(pattern, text_upper) for pattern in patterns):
            conditions.append(label)

    for label, patterns in ALLERGY_MAP.items():
        if any(re.search(pattern, text_upper) for pattern in patterns):
            allergies.append(label)

    for label, patterns in MEDICATION_MAP.items():
        if any(re.search(pattern, text_upper) for pattern in patterns):
            medications.append(label)

    risk_level = "Low"
    if allergies or "Warfarin" in medications:
        risk_level = "High"
    elif conditions or medications:
        risk_level = "Moderate"

    return {
        "conditions": sorted(set(conditions)),
        "allergies": sorted(set(allergies)),
        "medications": sorted(set(medications)),
        "risk_level": risk_level
    }


def parse_medical_text(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {"conditions": [], "allergies": [], "medications": [], "risk_level": "Low"}

    api_key = os.environ.get("GEMINI_API_KEY")
    samba_api_key = os.environ.get("SAMBANOVA_API_KEY")

    prompt = f"""
    Extract structured medical information from the following text.
    TEXT:
    {stripped}
    
    Extract all conditions/diseases, allergies (food/drug), and active medications.
    Assess risk_level as 'Low', 'Moderate', or 'High'. High = critical drugs (Warfarin) or life-threatening allergies.
    Return ONLY a JSON object with keys: "conditions", "allergies", "medications", "risk_level".
    """

    # 1. TRY GEMINI FIRST
    if api_key and _GENAI_AVAILABLE and len(stripped) >= 15:
        try:
            client = genai.Client(api_key=api_key)
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
                return {
                    "conditions": data.get("conditions", []),
                    "allergies": data.get("allergies", []),
                    "medications": data.get("medications", []),
                    "risk_level": data.get("risk_level", "Low"),
                }
        except Exception as e:
            print(f"[Parser] Gemini failed ({e}). Trying SambaNova fallback...")

    # 2. TRY SAMBANOVA FALLBACK
    if samba_api_key and _SAMBA_AVAILABLE and len(stripped) >= 15:
        try:
            client = SambaNova(api_key=samba_api_key, base_url="https://api.sambanova.ai/v1")
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a clinical parser. You must output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model="Meta-Llama-3.3-70B-Instruct",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            if response.choices[0].message.content:
                data = json.loads(response.choices[0].message.content)
                return {
                    "conditions": data.get("conditions", []),
                    "allergies": data.get("allergies", []),
                    "medications": data.get("medications", []),
                    "risk_level": data.get("risk_level", "Low"),
                }
        except Exception as e:
            print(f"[Parser] SambaNova fallback failed ({e}). Using Regex...")

    # 3. FINAL FALLBACK TO REGEX
    return _regex_parser(stripped)