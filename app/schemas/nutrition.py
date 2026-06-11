from pydantic import BaseModel
from typing import List

class NutritionProfile(BaseModel):
    avoided_foods: List[str]
    recommended_foods: List[str]
    nutrient_gaps: List[str]
