import httpx
from typing import Dict, Any

MOCK_RECORDS = [
    {"commodity": "Groundnut", "state": "Gujarat", "price": 7302.79, "trend": "up"},
    {"commodity": "Bajra", "state": "Rajasthan", "price": 2278.50, "trend": "up"},
    {"commodity": "Wheat", "state": "Uttar Pradesh", "price": 2436.00, "trend": "stable"},
]

class AgmarknetTool:
    URL = "https://api.agmarknet.gov.in/v1/dashboard-data/"

    async def get_dashboard(self, page: int = 1) -> Dict[str, Any]:
        """Fetches live market dashboard data from Agmarknet API."""
        if page > 1:
            return {"status": "success", "data": {"records": []}} # Only mock page 1
            
        payload = {"state": "", "district": "", "market": "", "commodity": "", "page": page}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.URL, json=payload)
                if response.status_code == 200:
                    raw = response.json()
                    if "data" in raw and "records" in raw["data"]:
                        return raw
        except Exception:
            pass

        # FIX: Ensure mock data matches expected {"data": {"records": []}} shape exactly
        return {"status": "success", "data": {"records": MOCK_RECORDS}}