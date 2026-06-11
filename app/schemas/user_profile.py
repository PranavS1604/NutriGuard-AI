from pydantic import BaseModel, Field
from typing import List, Optional

class UserProfile(BaseModel):
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    destination: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    medical_reports: List[str] = Field(default_factory=list)
    travel_history: List[str] = Field(default_factory=list)
    wearable_sources: List[str] = Field(default_factory=list)
