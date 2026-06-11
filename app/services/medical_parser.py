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

def parse_medical_text(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if not stripped: return {"conditions": [], "allergies": [], "medications": [], "risk_level": "Low"}

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and _GENAI_AVAILABLE and len(stripped) >= 15:
        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                "Extract structured medical information from the following text.\n"
                f"Text:\n{stripped}\n\n"
                "Extract all conditions/diseases, allergies, and active medications. "
                "Assess risk_level as 'Low', 'Moderate', or 'High' based on severity. Return only JSON."
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
                return {
                    "conditions": data.get("conditions", []),
                    "allergies": data.get("allergies", []),
                    "medications": data.get("medications", []),
                    "risk_level": data.get("risk_level", "Low"),
                }
        except Exception:
            pass

    return {"conditions": [], "allergies": [], "medications": [], "risk_level": "Low"}