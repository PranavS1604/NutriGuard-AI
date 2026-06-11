import os
import sys

# Ensure app is importable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.repositories import IFCTRepository, DrugRepository, CuisineRepository, USDARepository
from app.services.food_knowledge_service import FoodKnowledgeService

def test_repositories():
    print("Initializing repositories...")
    ifct = IFCTRepository()
    drug = DrugRepository()
    cuisine = CuisineRepository()
    usda = USDARepository()
    
    print("\n--- Testing IFCT Repository ---")
    ifct_res = ifct.search_food("Bajra")
    print(f"Searched 'Bajra', found {len(ifct_res)} results.")
    if ifct_res:
        print("First result:", ifct_res[0]["food_name"], "Tags:", ifct_res[0].get("tags"))
        
    print("\n--- Testing Drug Repository ---")
    drug_res = drug.find_interactions("Warfarin")
    print(f"Searched 'Warfarin', found {len(drug_res)} interactions.")
    for interaction in drug_res[:3]:
        print("-", interaction)
    print("Severity for Warfarin:", drug.get_severity("Warfarin"))
    
    print("\n--- Testing Cuisine Repository ---")
    cuisine_res = cuisine.get_dishes_by_cuisine("Japanese")
    print(f"Found {len(cuisine_res)} Japanese dishes.")
    if cuisine_res:
        print("First dish name:", cuisine_res[0]["name"])
        
    print("\n--- Testing USDA Repository ---")
    usda_res = usda.search_food("butter")
    print(f"Searched 'butter', found {len(usda_res)} results.")
    if usda_res:
        fdc_id = usda_res[0]["fdc_id"]
        nutrients = usda.get_nutrients(fdc_id)
        print("First product description:", usda_res[0]["description"])
        print(f"Found {len(nutrients)} nutrient values. Top 3:")
        for n in nutrients[:3]:
            print(f"  - {n['name']}: {n['amount']} {n['unit_name']}")

def test_service():
    print("\n==============================================")
    print("Initializing FoodKnowledgeService...")
    ifct = IFCTRepository()
    drug = DrugRepository()
    cuisine = CuisineRepository()
    usda = USDARepository()
    
    from app.tools.agmarknet_tool import AgmarknetTool
    from app.repositories import AgmarknetRepository
    import asyncio

    agmarknet_tool = AgmarknetTool()
    ag_repo = AgmarknetRepository(agmarknet_tool)

    service = FoodKnowledgeService(ifct, drug, cuisine, usda, ag_repo)
    
    print("\n--- Service: Live Prices (Agmarknet) ---")
    prices = asyncio.run(service.get_live_prices())
    print(f"Retrieved {len(prices)} live commodity prices from Agmarknet. Examples:")
    for fp in prices[:3]:
        print(f"  - {fp.commodity}: Modal Price ₹{fp.price:.2f} ({fp.trend})")
        
    print("\n--- Service: Price for Specific Food (Bajra) ---")
    price_bajra = asyncio.run(service.get_price_for_food("Bajra"))
    if price_bajra:
        print(f"  - {price_bajra.commodity} found: ₹{price_bajra.price:.2f} ({price_bajra.trend})")
    
    print("\n--- Service: Food Nutrition (IFCT) ---")
    nut1 = service.get_food_nutrition("Bajra")
    print("Bajra:", nut1)
    
    print("\n--- Service: Food Nutrition (USDA Fallback) ---")
    nut2 = service.get_food_nutrition("butter, with salt")
    print("Butter (with salt):", nut2)

    print("\n--- Service: Food Nutrition (USDA Fallback - different food) ---")
    nut3 = service.get_food_nutrition("egg")
    print("Egg:", nut3)
    
    print("\n--- Service: Drug Interactions ---")
    interactions = service.get_drug_interactions(["Warfarin", "Atorvastatin"])
    print("Interactions for ['Warfarin', 'Atorvastatin']:")
    for interaction in interactions:
        print(f"Medication: {interaction['medication']}, Severity: {interaction['severity']}")
        for warning in interaction['warnings'][:2]:
            print(f"  - {warning}")
            
    print("\n--- Service: Cuisine Risks & Safety ---")
    destination = "Japan"
    avoided = ["peanut", "sesame"]
    high_risk = service.find_high_risk_dishes(destination, avoided)
    safe = service.find_safe_dishes(destination, avoided)
    print(f"In {destination} avoiding {avoided}:")
    print(f"  - Safe dishes count: {len(safe)}")
    print(f"  - High risk dishes count: {len(high_risk)}")
    if high_risk:
        print("  - Example high risk dish:", high_risk[0]["dish_name"], "contains:", high_risk[0]["matched_ingredients"])
        
    print("\n--- Service: Recommend Meals ---")
    meals = service.recommend_meals(destination, avoided)
    print("Recommended meals:")
    for meal in meals[:3]:
        print("  -", meal)

if __name__ == "__main__":
    test_repositories()
    test_service()
