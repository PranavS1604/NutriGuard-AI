from app.schemas.context import MissionContext
from app.schemas.travel_risk import TravelRiskResult
from app.tools.travel_risk import check_travel_risks

class TravelAgent:
    async def run(self, context: MissionContext) -> TravelRiskResult:
        """
        Assesses travel risks and regional parameters for the destination.
        """
        # Get travel risk assessment
        risk_assessment = await check_travel_risks(context.destination)
        
        # Placeholder: Actual implementation would consider health profile
        return risk_assessment
