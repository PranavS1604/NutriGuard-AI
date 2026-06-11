from typing import List, Dict, Any, Optional
from app.repositories.ifct_repository import IFCTRepository
from app.repositories.drug_repository import DrugRepository
from app.repositories.cuisine_repository import CuisineRepository
from app.repositories.usda_repository import USDARepository
from app.repositories.agmarknet_repository import AgmarknetRepository
from app.schemas.food_price import FoodPrice

class FoodKnowledgeService:
    def __init__(
        self,
        ifct_repo: IFCTRepository,
        drug_repo: DrugRepository,
        cuisine_repo: CuisineRepository,
        usda_repo: USDARepository,
        agmarknet_repo: AgmarknetRepository = None
    ):
        self.ifct_repo = ifct_repo
        self.drug_repo = drug_repo
        self.cuisine_repo = cuisine_repo
        self.usda_repo = usda_repo
        self.agmarknet_repo = agmarknet_repo

    async def get_live_prices(self) -> List[FoodPrice]:
        """
        Retrieves live agricultural market pricing from Agmarknet API.
        """
        if self.agmarknet_repo:
            return await self.agmarknet_repo.get_live_prices()
        return []

    async def get_price_for_food(self, food: str) -> Optional[FoodPrice]:
        """
        Lookup live market pricing for a specific commodity/food.
        """
        if self.agmarknet_repo:
            return await self.agmarknet_repo.get_price_for_food(food)
        return None

    def get_food_nutrition(self, food_name: str) -> Dict[str, Any]:
        """
        Retrieves nutrition data across IFCT and USDA for a given food.
        """
        # Try IFCT first
        ifct_results = self.ifct_repo.search_food(food_name)
        if ifct_results:
            return {
                "source": "IFCT",
                "food_name": ifct_results[0].get("food_name"),
                "protein_g": ifct_results[0].get("protein_g"),
                "fat_g": ifct_results[0].get("fat_g"),
                "carbohydrates_g": ifct_results[0].get("carbohydrates_g"),
                "energy_kj": ifct_results[0].get("energy_kj"),
                "tags": ifct_results[0].get("tags", "")
            }
        
        # Fallback to USDA
        usda_results = self.usda_repo.search_food(food_name)
        if usda_results:
            fdc_id = usda_results[0].get("fdc_id")
            nutrients = self.usda_repo.get_nutrients(fdc_id)
            
            if not nutrients:
                return {} # No nutrient data found for this USDA food

            # map to common structure
            mapped_nutrients = {n["name"].lower(): n["amount"] for n in nutrients}
            # Handle potential missing or different nutrient names
            protein_g = mapped_nutrients.get("protein", 0) if mapped_nutrients.get("protein") is not None else mapped_nutrients.get("protein, total", 0)
            fat_g = mapped_nutrients.get("total lipid (fat)", 0) if mapped_nutrients.get("total lipid (fat)") is not None else mapped_nutrients.get("fat, total", 0)
            carbohydrates_g = mapped_nutrients.get("carbohydrate, by difference", 0) if mapped_nutrients.get("carbohydrate, by difference") is not None else mapped_nutrients.get("carbohydrates, total", 0)
            energy_kcal = mapped_nutrients.get("energy", 0)
            energy_kj = energy_kcal * 4.184 if energy_kcal else 0

            return {
                "source": "USDA",
                "food_name": usda_results[0].get("description"),
                "protein_g": protein_g,
                "fat_g": fat_g,
                "carbohydrates_g": carbohydrates_g,
                "energy_kj": energy_kj,
                "tags": ""
            }
        
        return {}

    def get_drug_interactions(self, medications: List[str]) -> List[Dict[str, Any]]:
        """
        Looks up food-drug interactions for a list of patient medications.
        """
        results = []
        for med in medications:
            warnings = self.drug_repo.get_food_warnings(med)
            severity = self.drug_repo.get_severity(med)
            if warnings:
                results.append({
                    "medication": med,
                    "warnings": warnings,
                    "severity": severity
                })
        return results

    def _dish_matches_ingredients(self, dish: Dict[str, Any], ingredients: List[str]) -> List[str]:
        """
        Helper to find which of the blacklisted ingredients are mentioned in a dish's attributes.
        """
        found = []
        # Join text fields to search
        text_to_search = " ".join([
            str(dish.get("name", "")),
            str(dish.get("alias", "")),
            str(dish.get("coarse_categories", "")),
            str(dish.get("fine_categories", "")),
            str(dish.get("ingredients", "")),
            str(dish.get("text_description", ""))
        ]).lower()
        
        for ing in ingredients:
            if ing.lower() in text_to_search:
                found.append(ing)
        return found

    def get_dish_details(self, dish_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves detailed information about a dish from the CuisineRepository.
        """
        return self.cuisine_repo.get_dish_details(dish_name)

    def _get_dishes_for_destination(self, destination: str) -> List[Dict[str, Any]]:
        """
        Helper to fetch and merge dishes matching normalized country or cuisine.
        """
        from app.services.destination_normalizer import normalize_destination
        norm = normalize_destination(destination)
        country = norm["country"]
        cuisine = norm["cuisine"]
        
        dishes_country = self.cuisine_repo.get_dishes_by_country(country)
        dishes_cuisine = self.cuisine_repo.get_dishes_by_cuisine(cuisine)
        
        seen = set()
        merged = []
        for dish in dishes_country + dishes_cuisine:
            name = dish.get("name")
            if name and name not in seen:
                seen.add(name)
                merged.append(dish)
        return merged

    def find_safe_dishes(self, destination: str, avoided_foods: List[str]) -> List[Dict[str, Any]]:
        """
        Finds dishes in the destination country/cuisine that do NOT contain avoided foods/allergens.
        """
        dishes = self._get_dishes_for_destination(destination)
        safe_dishes = []
        for dish in dishes:
            matches = self._dish_matches_ingredients(dish, avoided_foods)
            if not matches:
                safe_dishes.append(dish)
        return safe_dishes

    def find_high_risk_dishes(self, destination: str, avoided_foods: List[str]) -> List[Dict[str, Any]]:
        """
        Finds dishes in the destination country/cuisine that contain avoided foods/allergens.
        """
        dishes = self._get_dishes_for_destination(destination)
        high_risk = []
        for dish in dishes:
            matches = self._dish_matches_ingredients(dish, avoided_foods)
            if matches:
                high_risk.append({
                    "dish_name": dish.get("name"),
                    "matched_ingredients": matches,
                    "description": dish.get("text_description")
                })
        return high_risk

    def recommend_meals(self, destination: str, avoided_foods: List[str]) -> List[str]:
        """
        Generates meal recommendations based on safe local dishes.
        """
        safe_dishes = self.find_safe_dishes(destination, avoided_foods)
        recommendations = []
        for dish in safe_dishes[:5]:  # limit to top 5 recommendations
            name = dish.get("name")
            desc = dish.get("text_description")
            if desc and len(desc) > 100:
                desc = desc[:100] + "..."
            recommendations.append(f"{name}: {desc}")
        
        if not recommendations:
            recommendations = ["Ensure to stick with whole foods like grilled meats, steamed rice, and fresh vegetables."]
        return recommendations
