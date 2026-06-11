"""
orchestrator.py — Executes the full NutriGuard AI multi-agent mission.
"""
from app.schemas.context import MissionContext
from app.schemas.mission import MissionResult
from app.agents.health_agent import HealthAgent
from app.agents.nutrition_agent import NutritionAgent
from app.agents.travel_agent import TravelAgent
from app.agents.safety_agent import SafetyAgent

from app.repositories import IFCTRepository, DrugRepository, CuisineRepository, USDARepository, AgmarknetRepository
from app.tools.agmarknet_tool import AgmarknetTool
from app.services.food_knowledge_service import FoodKnowledgeService

async def execute_travel_health_mission(
    user_id: str,
    destination: str,
    metadata: dict = None
) -> MissionResult:
    """
    Executes the travel health orchestrator mission.

    Flow:
    1. Health Agent: Analyzes user lab reports and prescriptions to build a profile.
    2. Nutrition Agent: Analyzes profile to provide nutritional guidelines.
    3. Travel Agent: Assesses risks related to the destination (e.g., Tokyo).
    4. Safety Agent: Aggregates medical/allergy risks and defines safety guidelines.
    5. Generate Outputs: Produces emergency/waiter card and summary.
    """
    # Initialize Knowledge Layer Repositories & Service
    ifct_repo = IFCTRepository()
    drug_repo = DrugRepository()
    cuisine_repo = CuisineRepository()
    usda_repo = USDARepository()

    agmarknet_tool = AgmarknetTool()
    agmarknet_repo = AgmarknetRepository(agmarknet_tool)

    food_knowledge_service = FoodKnowledgeService(
        ifct_repo, drug_repo, cuisine_repo, usda_repo, agmarknet_repo
    )

    from app.services.destination_normalizer import normalize_destination
    norm = normalize_destination(destination)
    normalized_dest = norm["country"]
    dest_lang = norm["language"]
    dest_cuisine = norm["cuisine"]

    # Create mission context
    context = MissionContext(
        user_id=user_id,
        mission_id=f"mission_{user_id}_{destination.replace(' ', '_')}",
        destination=normalized_dest,
        current_step="Initializing",
        medical_reports=[],
        recommended_foods=[],  # No hardcoded foods — populated dynamically
        destination_language=dest_lang,
        metadata=metadata or {}
    )

    # Initialize agents with shared food knowledge service
    health_agent = HealthAgent()
    nutrition_agent = NutritionAgent(food_knowledge_service)
    travel_agent = TravelAgent()
    safety_agent = SafetyAgent(food_knowledge_service)

    # 1. Health Agent Analysis
    health_profile = await health_agent.run(context)

    # 2. Nutrition Agent Guidelines
    nutrition_profile = await nutrition_agent.run(context, health_profile)

    # 3. Travel Agent Risk Assessment
    travel_risk_result = await travel_agent.run(context)

    # 4. Safety Agent Verification
    risk_assessment = await safety_agent.run(
        context,
        health_profile,
        nutrition_profile,
        travel_risk_result
    )

    # Determine local safe/recommended dishes to build meal plan
    safe_dishes = food_knowledge_service.find_safe_dishes(destination, nutrition_profile.avoided_foods)
    meal_plan = []
    for dish in safe_dishes[:5]:
        name = dish.get('name', 'Unknown dish')
        desc = str(dish.get('text_description', '') or '').strip()
        if desc and len(desc) > 120:
            desc = desc[:120] + "..."
        meal_plan.append(f"{name}: {desc}" if desc else name)

    if not meal_plan:
        # Generic fallback only when no cuisine data found for this destination
        meal_plan = [
            "Steamed rice with grilled vegetables — safe base meal",
            "Grilled or baked lean protein (chicken, fish) without heavy sauces",
            "Fresh fruit salad — request ingredients list to verify allergens"
        ]

    # 5. Output Generation — Dynamic Google Maps hospital lookup
    from app.tools.google_maps_tool import GoogleMapsTool
    maps_tool = GoogleMapsTool()
    hospitals = maps_tool.find_hospitals(destination)
    hospital_names = [h.get("name", "Unknown Hospital") for h in hospitals[:3]]
    if not hospital_names:
        hospital_names = [f"Local Emergency Medical Center — {normalized_dest}"]

    # Build health summary
    cond_count = len(health_profile.conditions)
    allergy_count = len(health_profile.allergies)
    med_count = len(health_profile.medications)

    if cond_count == 0 and allergy_count == 0 and med_count == 0:
        health_summary = "No medical conditions, allergies, or medications detected. General travel health precautions apply."
    else:
        parts = []
        if cond_count:
            parts.append(f"{cond_count} condition(s): {', '.join(health_profile.conditions)}")
        if allergy_count:
            parts.append(f"{allergy_count} allergy/allergies: {', '.join(health_profile.allergies)}")
        if med_count:
            parts.append(f"{med_count} medication(s): {', '.join(health_profile.medications)}")
        health_summary = "Detected — " + " | ".join(parts)

    return MissionResult(
        mission_id=context.mission_id,
        health_summary=health_summary,
        overall_risk=risk_assessment.overall_risk,
        risks=risk_assessment.medical_risks + risk_assessment.food_risks + risk_assessment.travel_risks,
        meal_plan=meal_plan,
        emergency_actions=risk_assessment.recommendations,
        hospital_recommendations=hospital_names,
        destination_advisories=travel_risk_result.travel_risks,
        waiter_card_url=risk_assessment.emergency_card_url,
        waiter_card_translation=getattr(risk_assessment, 'waiter_card_translation', None),
        health_profile={
            "conditions": health_profile.conditions,
            "allergies": health_profile.allergies,
            "medications": health_profile.medications,
            "risk_level": health_profile.risk_level
        },
        destination_info={
            "country": normalized_dest,
            "cuisine": dest_cuisine,
            "language": dest_lang
        },
        generated_at=context.created_at
    )
