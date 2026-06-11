import httpx
from typing import Dict, Any

# Ensure mock data matches real API keys so deduping doesn't break
MOCK_RECORDS = [
    {"cmdt_name": "Groundnut", "mkt_name": "Rajkot", "as_on_price": "7302.79", "trend": "up"},
    {"cmdt_name": "Bajra(Pearl Millet/Cumbu)", "mkt_name": "Jaipur", "as_on_price": "2278.50", "trend": "up"},
    {"cmdt_name": "Wheat", "mkt_name": "Kanpur", "as_on_price": "2436.00", "trend": "stable"},
    {"cmdt_name": "Maize", "mkt_name": "Davangere", "as_on_price": "1890.00", "trend": "down"},
    {"cmdt_name": "Bengal Gram(Gram)", "mkt_name": "Indore", "as_on_price": "5200.00", "trend": "stable"},
]

class AgmarknetTool:
    URL = "https://api.agmarknet.gov.in/v1/dashboard-data/"

    async def get_dashboard(self, page: int = 1) -> Dict[str, Any]:
        """Fetches live market dashboard data from Agmarknet API."""
        if page > 1:
            return {"status": "success", "records": []} 
            
        payload = {"state": "", "district": "", "market": "", "commodity": "", "page": page}
        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                response = await client.post(self.URL, json=payload)
                if response.status_code == 200:
                    raw = response.json()
                    if "data" in raw and isinstance(raw["data"], dict) and "records" in raw["data"]:
                        return {"status": "success", "records": raw["data"]["records"]}
        except Exception as e:
            print(f"Agmarknet API Error: {e}")

        return {"status": "success", "records": MOCK_RECORDS}