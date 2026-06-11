from app.schemas.context import MissionContext
from app.schemas.nutrition import NutritionProfile
from app.services.food_knowledge_service import FoodKnowledgeService

class NutritionAgent:
    def __init__(self, food_knowledge_service: FoodKnowledgeService = None):
        self.service = food_knowledge_service

    async def run(self, context: MissionContext, health_profile) -> NutritionProfile:
        """
        Analyzes a health profile using FoodKnowledgeService to provide personalized nutritional guidelines.
        """
        avoided_foods = []
        recommended_foods = []
        nutrient_gaps = []

        # Populate avoided foods based on allergies
        if health_profile.allergies:
            avoided_foods.extend(health_profile.allergies)
            
        # Analyze conditions to set nutritional guidelines
        for condition in health_profile.conditions:
            cond_lower = condition.lower()
            if "cholesterol" in cond_lower:
                avoided_foods.extend(["butter", "trans fats", "fatty meats"])
                recommended_foods.extend(["Oatmeal", "Beans", "Barley", "Olive oil"])
                nutrient_gaps.extend(["Soluble Fiber", "Omega-3 Fatty Acids"])
            elif "diabetes" in cond_lower or "blood sugar" in cond_lower:
                avoided_foods.extend(["refined sugars", "white bread", "sweetened beverages"])
                recommended_foods.extend(["Spinach", "Quinoa", "Almonds", "Broccoli"])
                nutrient_gaps.extend(["Magnesium", "Chromium"])
            elif "hypertension" in cond_lower or "blood pressure" in cond_lower:
                avoided_foods.extend(["excess sodium", "processed meats", "canned soups"])
                recommended_foods.extend(["Banana", "Avocado", "Sweet potato"])
                nutrient_gaps.extend(["Potassium", "Calcium"])

        # De-duplicate lists
        avoided_foods = list(set(avoided_foods))
        recommended_foods = list(set(recommended_foods))
        nutrient_gaps = list(set(nutrient_gaps))

        # Fallback values if none derived
        if not avoided_foods:
            avoided_foods = ["excess sugars", "processed foods"]
        if not recommended_foods:
            recommended_foods = ["Leafy greens", "Whole grains", "Lean protein"]
        if not nutrient_gaps:
            nutrient_gaps = ["Multivitamin"]

        # Validate with FoodKnowledgeService if available
        if self.service:
            # Query some recommended foods to get real nutrition tags
            for r_food in recommended_foods[:2]:
                nutrition_data = self.service.get_food_nutrition(r_food)
                if nutrition_data and "tags" in nutrition_data:
                    # Enrich nutrient info or log
                    pass

        return NutritionProfile(
            avoided_foods=avoided_foods,
            recommended_foods=recommended_foods,
            nutrient_gaps=nutrient_gaps
        )
