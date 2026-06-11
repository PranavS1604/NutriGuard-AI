from pydantic import BaseModel
from typing import List

class TravelRiskResult(BaseModel):
    destination: str
    medical_risks: List[str]
    food_risks: List[str]
    travel_risks: List[str]
    overall_risk: str