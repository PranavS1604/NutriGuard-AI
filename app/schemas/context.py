from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Optional

from typing import List

class MissionContext(BaseModel):
    user_id: str
    mission_id: str
    destination: str
    current_step: str
    metadata: Dict[str, str] = Field(default_factory=dict)
    medical_reports: List[bytes] = Field(default_factory=list)
    recommended_foods: List[str] = Field(default_factory=list)
    destination_language: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
