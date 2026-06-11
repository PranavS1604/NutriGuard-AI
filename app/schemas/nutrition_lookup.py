from pydantic import BaseModel

class NutritionLookupResult(BaseModel):
    food_name: str
    calories: float
    protein: float
    carbohydrates: float
    fat: float