from app.schemas.travel_risk import TravelRiskResult

async def check_travel_risks(destination: str) -> TravelRiskResult:
    """
    Simulates checking regional/country-specific health and travel advisory risks.
    """
    return TravelRiskResult(
        destination=destination,
        medical_risks=["Local health advisories"],
        food_risks=["Street food contamination risk"],
        travel_risks=["Transportation disruptions"],
        overall_risk="Moderate"
    )
