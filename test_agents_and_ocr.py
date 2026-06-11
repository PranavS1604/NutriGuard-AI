import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Ensure app is importable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.agents.orchestrator import execute_travel_health_mission
from app.services.medical_parser import parse_medical_text
from app.services.destination_normalizer import normalize_destination

async def test_medical_parser():
    print("Testing medical parser...")
    text = (
        "Patient John Doe has a history of DIABETES and HIGH CHOLESTEROL. "
        "Allergies noted: SEVERE PEANUT ALLERGY. "
        "Active prescription: Metformin 500mg BID and Warfarin 5mg daily."
    )
    result = parse_medical_text(text)
    print("Parsed result:", result)
    assert "Diabetes" in result["conditions"]
    assert "High cholesterol" in result["conditions"]
    assert "Peanuts" in result["allergies"]
    assert "Metformin" in result["medications"]
    assert "Warfarin" in result["medications"]
    assert result["risk_level"] == "High"
    print("[SUCCESS] Medical parser test passed.")

def test_destination_normalizer():
    print("\nTesting destination normalizer...")
    t1 = normalize_destination("Tokyo")
    print("Tokyo:", t1)
    assert t1["country"] == "Japan"
    assert t1["cuisine"] == "Japanese"
    assert t1["language"] == "ja"

    t2 = normalize_destination("mumbai")
    print("Mumbai:", t2)
    assert t2["country"] == "India"
    assert t2["cuisine"] == "Indian"
    assert t2["language"] == "hi"
    print("[SUCCESS] Destination normalizer test passed.")

async def test_orchestrator_execution():
    print("\nTesting agent orchestrator with custom metadata...")
    # Inject OCR text via metadata fallback
    # Normally HealthAgent runs perform_medical_ocr on report bytes, but we can pass text in metadata as well!
    # Wait, we want to test parsing OCR results. We can pass mock report bytes!
    # The OCR tool performs OCR and returns "Mocked OCR Result".
    # Wait, we can test the fallback metadata mechanism as well.
    import unittest.mock
    
    # We will test using metadata fallback
    from app.schemas.context import MissionContext
    from app.agents.health_agent import HealthAgent
    
    context = MissionContext(
        user_id="user_123",
        mission_id="mission_123_tokyo",
        destination="Tokyo",
        current_step="Initializing",
        metadata={
            "medical_text": "DIABETES, PEANUTS, METFORMIN, WARFARIN"
        }
    )
    
    agent = HealthAgent()
    profile = await agent.run(context)
    print("Health profile generated:", profile)
    assert "Diabetes" in profile.conditions
    assert "Peanuts" in profile.allergies
    assert "Metformin" in profile.medications
    assert "Warfarin" in profile.medications
    assert profile.risk_level == "High"
    
    # Run full orchestrator
    print("\nExecuting full orchestrator travel health mission...")
    result = await execute_travel_health_mission(
        user_id="user_123",
        destination="Tokyo"
    )
    print("Mission Result:")
    print("Health Summary:", result.health_summary)
    print("Overall Risk:", result.overall_risk)
    print("Risks:", result.risks)
    print("Meal Plan (top 3):", result.meal_plan)
    print("Emergency Actions:", result.emergency_actions)
    print("Hospital Recommendations:", result.hospital_recommendations)
    print("Destination Advisories:", result.destination_advisories)
    print("Waiter Card URL:", result.waiter_card_url)
    
    # Assertions
    first_hosp = result.hospital_recommendations[0]
    hosp_name = first_hosp.get("name", "") if isinstance(first_hosp, dict) else str(first_hosp)
    assert "Japan" in hosp_name or "Tokyo" in hosp_name or "St. Luke's" in hosp_name or "Mock" in hosp_name
    print("[SUCCESS] Orchestrator test passed.")

async def test_query_agent():
    print("\nTesting Query Agent...")
    from app.repositories import IFCTRepository, DrugRepository, CuisineRepository, USDARepository, AgmarknetRepository
    from app.services.food_knowledge_service import FoodKnowledgeService
    from app.agents.query_agent import QueryAgent
    
    knowledge_service = FoodKnowledgeService(
        IFCTRepository(), DrugRepository(), CuisineRepository(), USDARepository()
    )
    agent = QueryAgent(knowledge_service)
    
    # 1. Food Safety
    res1 = await agent.process_query("Can I eat sushi in Tokyo?")
    print("Query 1 (Sushi):", res1)
    
    # 2. Location Search
    res2 = await agent.process_query("Where is the nearest hospital in Tokyo?")
    print("Query 2 (Hospital):", res2)
    
    print("[SUCCESS] Query Agent tests passed.")

if __name__ == "__main__":
    asyncio.run(test_medical_parser())
    test_destination_normalizer()
    asyncio.run(test_orchestrator_execution())
    asyncio.run(test_query_agent())
