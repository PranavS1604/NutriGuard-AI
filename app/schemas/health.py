from pydantic import BaseModel
from typing import List, Optional

class HealthProfile(BaseModel):
    conditions: List[str]
    allergies: List[str]
    medications: List[str]

    cholesterol: Optional[float] = None
    blood_sugar: Optional[float] = None

    risk_level: str
