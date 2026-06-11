from app.schemas.nutrition_lookup import NutritionLookupResult

async def lookup_nutrition(food_item: str) -> NutritionLookupResult:
    """
    Simulates looking up nutritional information or ingredient details.
    """
    return NutritionLookupResult(
        food_name=food_item,
        calories=300,
        protein=20,
        carbohydrates=40,
        fat=10
    )
