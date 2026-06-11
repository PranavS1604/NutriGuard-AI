from pydantic import BaseModel

class FoodPrice(BaseModel):
    commodity: str
    price: float
    trend: str
