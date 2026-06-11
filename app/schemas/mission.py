from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any

class MissionResult(BaseModel):
    mission_id: str
    health_summary: str
    overall_risk: str
    risks: List[str]
    meal_plan: List[str]
    emergency_actions: List[str]
    hospital_recommendations: List[Any]
    destination_advisories: List[str]
    waiter_card_url: str
    waiter_card_translation: Optional[str] = None  # Gemini-translated emergency card text
    health_profile: Optional[Dict[str, Any]] = None  # Structured health profile from parsing
    destination_info: Optional[Dict[str, str]] = None  # Normalized destination metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
