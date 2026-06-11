from app.schemas.context import MissionContext
from app.schemas.risk import RiskAssessment
from app.tools.emergency_card import generate_emergency_card
from app.services.food_knowledge_service import FoodKnowledgeService
from app.services.medication_cuisine_engine import get_local_cuisine_drug_risks, format_risk_warnings

class SafetyAgent:
    def __init__(self, food_knowledge_service: FoodKnowledgeService = None):
        self.service = food_knowledge_service

    async def run(
        self,
        context: MissionContext,
        health_profile,
        nutrition_profile,
        travel_risk_result
    ) -> RiskAssessment:
        """
        Aggregates all agent outputs to perform a unified medical, drug, and environmental safety risk assessment.
        """
        medical_risks = []
        food_risks = []
        recommendations = [
            "Carry emergency medical documentation in local language at all times",
            "Show your personalized digital waiter card before ordering meals"
        ]

        # 1. Get real Food-Drug Interactions using the FoodKnowledgeService
        if self.service and health_profile.medications:
            interactions = self.service.get_drug_interactions(health_profile.medications)
            for item in interactions:
                med = item["medication"]
                severity = item["severity"]
                for warning in item["warnings"]:
                    medical_risks.append(f"[{severity} Severity] Interaction for {med}: {warning}")
        
        # 2. Medication ↔ Local Cuisine Risk Engine (NEW - hackathon differentiator)
        if health_profile.medications and context.destination:
            cuisine_risks = get_local_cuisine_drug_risks(health_profile.medications, context.destination)
            if cuisine_risks:
                cuisine_warnings = format_risk_warnings(cuisine_risks)
                medical_risks.extend(cuisine_warnings)
                # Add specific dish avoidance recommendations
                for cr in cuisine_risks:
                    for dish in cr.get("specific_dishes_to_avoid", [])[:2]:
                        recommendations.append(f"[{cr['severity']}] Avoid '{dish}' — dangerous interaction with {cr['medication']}")

        if not medical_risks:
            medical_risks.append("No critical food-drug interactions detected for active medications.")

        # 3. Get high-risk dishes in the local destination using CuisineRepository via Service
        if self.service and nutrition_profile.avoided_foods:
            high_risk_dishes = self.service.find_high_risk_dishes(context.destination, nutrition_profile.avoided_foods)
            for dish in high_risk_dishes[:4]: # limit to top 4 risk examples
                dish_name = dish["dish_name"]
                matched = ", ".join(dish["matched_ingredients"])
                food_risks.append(f"Dish '{dish_name}' contains avoided ingredients: {matched}")
                recommendations.append(f"Avoid ordering '{dish_name}' due to high risk of allergen contamination")
                
        if not food_risks:
            food_risks.append("No direct dish risks identified for the specified destination.")

        # Determine overall risk level
        all_risk_text = " ".join(medical_risks + food_risks).lower()

        if "[critical]" in all_risk_text or "critical severity" in all_risk_text:
            overall_risk = "Critical"
        elif (
            "[high]" in all_risk_text
            or "high severity" in all_risk_text
            or len([r for r in food_risks if "contains" in r]) >= 3
        ):
            overall_risk = "High"
        elif (
            "[moderate]" in all_risk_text
            or "medium severity" in all_risk_text
            or food_risks[0] != "No specific high-risk dishes identified for your allergen profile at this destination."
            or medical_risks[0] != "No critical food-drug interactions detected for your medications at this destination."
        ):
            overall_risk = "Moderate"
        else:
            overall_risk = "Low"

        # Generate emergency card
        emergency_card = await generate_emergency_card(
            context.user_id,
            health_profile.conditions + health_profile.allergies,
            nutrition_profile.avoided_foods,
            context.destination_language
        )
        
        return RiskAssessment(
            overall_risk=overall_risk,
            medical_risks=medical_risks,
            food_risks=food_risks,
            travel_risks=travel_risk_result.travel_risks,
            recommendations=recommendations,
            emergency_card_url=emergency_card.card_url,
            waiter_card_translation=emergency_card.translated_text or None
        )
