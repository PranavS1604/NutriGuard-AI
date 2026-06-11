import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

class MedicalProfile(BaseModel):
    conditions: list[str] = Field(description="List of medical conditions or diseases")
    allergies: list[str] = Field(description="List of food or drug allergies")
    medications: list[str] = Field(description="List of medications the patient is taking")
    risk_level: str = Field(description="Assess risk level as Low, Moderate, or High based on conditions and medications")

def _parse_medical_text_fallback(text: str) -> Dict[str, Any]:
    text_upper = text.upper()
    
    CONDITIONS_MAP = {
        r"\bDIABETES\b": "Diabetes",
        r"\bHYPERTENSION\b": "Hypertension",
        r"\bCHOLESTEROL\b": "High cholesterol",
        r"\bHIGH CHOLESTEROL\b": "High cholesterol",
        r"\bHYPERLIPIDEMIA\b": "High cholesterol"
    }
    ALLERGIES_MAP = {
        r"\bPEANUT(S)?\b": "Peanuts",
        r"\bMILK\b": "Milk",
        r"\bLACTOSE\b": "Milk",
        r"\bSHELLFISH\b": "Shellfish",
        r"\bSHRIMP\b": "Shellfish",
        r"\bSESAME\b": "Sesame"
    }
    MEDICATIONS_MAP = {
        r"\bWARFARIN\b": "Warfarin",
        r"\bCOUMADIN\b": "Warfarin",
        r"\bATORVASTATIN\b": "Atorvastatin",
        r"\bLIPITOR\b": "Atorvastatin",
        r"\bMETFORMIN\b": "Metformin",
        r"\bGLUCOPHAGE\b": "Metformin",
        r"\bSTATIN(S)?\b": "Statins"
    }
    
    conditions = []
    for pattern, val in CONDITIONS_MAP.items():
        if re.search(pattern, text_upper):
            conditions.append(val)
    allergies = []
    for pattern, val in ALLERGIES_MAP.items():
        if re.search(pattern, text_upper):
            allergies.append(val)
    medications = []
    for pattern, val in MEDICATIONS_MAP.items():
        if re.search(pattern, text_upper):
            medications.append(val)
            
    conditions = list(set(conditions))
    allergies = list(set(allergies))
    medications = list(set(medications))
    
    risk_level = "Low"
    if "Warfarin" in medications or "Peanuts" in allergies:
        risk_level = "High"
    elif conditions or medications or allergies:
        risk_level = "Moderate"
        
    return {
        "conditions": conditions,
        "allergies": allergies,
        "medications": medications,
        "risk_level": risk_level
    }

def parse_medical_text(text: str) -> Dict[str, Any]:
    """
    Parses a string of text (e.g. from an OCR output or lab report)
    to extract conditions, allergies, and medications.
    Tries Gemini LLM first, falls back to regex.
    """
    if len(text.strip()) < 50:
        return _parse_medical_text_fallback(text)
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and genai:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Extract structured medical information from the following OCR text:\n\n{text}"
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MedicalProfile,
                    temperature=0.1
                )
            )
            
            if response.text:
                import json
                return json.loads(response.text)
        except Exception as e:
            print(f"Gemini LLM extraction failed: {e}. Falling back to regex.")
            
    # Fallback to regex
    return _parse_medical_text_fallback(text)
