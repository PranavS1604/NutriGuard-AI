from app.schemas.food_price import FoodPriceResult

async def lookup_food_price(food_item: str, location: str) -> FoodPriceResult:
    """
    Simulates looking up grocery or market prices for specific foods at the destination.
    """
    return FoodPriceResult(
        food_name=food_item,
        destination=location,
        average_price=10.99,
        currency="USD",
        price_range="$8-$12"
    )
