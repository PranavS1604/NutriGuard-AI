from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class TravelProfile(BaseModel):
    origin: str
    destination: str
    departure_date: date
    return_date: date

class RiskAssessment(BaseModel):
    overall_risk: str
    medical_risks: List[str]
    food_risks: List[str]
    travel_risks: List[str]
    recommendations: List[str]
    emergency_card_url: str
    waiter_card_translation: Optional[str] = None  # Gemini-translated text for waiter card
