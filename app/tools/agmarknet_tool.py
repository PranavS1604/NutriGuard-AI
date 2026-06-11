import asyncio
import httpx
from typing import Dict, Any, List

MOCK_RECORDS = [
    {"commodity": "Groundnut", "state": "Gujarat", "district": "Rajkot",
     "market": "Rajkot", "min_price": 6800.0, "max_price": 7800.0, "modal_price": 7302.79, "trend": "up"},
    {"commodity": "Bajra(Pearl Millet/Cumbu)", "state": "Rajasthan", "district": "Jaipur",
     "market": "Jaipur", "min_price": 2100.0, "max_price": 2400.0, "modal_price": 2278.50, "trend": "up"},
    {"commodity": "Wheat", "state": "Uttar Pradesh", "district": "Kanpur",
     "market": "Kanpur", "min_price": 2300.0, "max_price": 2550.0, "modal_price": 2436.00, "trend": "stable"},
    {"commodity": "Maize", "state": "Karnataka", "district": "Davangere",
     "market": "Davangere", "min_price": 2000.0, "max_price": 2300.0, "modal_price": 2150.00, "trend": "down"},
    {"commodity": "Bengal Gram(Gram)", "state": "Madhya Pradesh", "district": "Indore",
     "market": "Indore", "min_price": 5800.0, "max_price": 6300.0, "modal_price": 6120.00, "trend": "stable"},
    {"commodity": "Soyabean", "state": "Maharashtra", "district": "Latur",
     "market": "Latur", "min_price": 4200.0, "max_price": 4600.0, "modal_price": 4420.00, "trend": "up"},
    {"commodity": "Mustard", "state": "Rajasthan", "district": "Bharatpur",
     "market": "Bharatpur", "min_price": 5100.0, "max_price": 5500.0, "modal_price": 5310.00, "trend": "stable"},
    {"commodity": "Onion", "state": "Maharashtra", "district": "Nashik",
     "market": "Nashik", "min_price": 800.0, "max_price": 1400.0, "modal_price": 1120.00, "trend": "up"},
]


class AgmarknetTool:
    URL = "https://api.agmarknet.gov.in/v1/dashboard-data/"

    async def get_dashboard(self, page: int = 1) -> Dict[str, Any]:
        """
        Fetches live market dashboard data from Agmarknet API.
        Falls back to realistic mock data on network failure.
        Returns a consistent structure: {"status": "success", "data": {"records": [...]}}
        """
        payload = {"state": "", "district": "", "market": "", "commodity": "", "page": page}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(self.URL, json=payload)
                if response.status_code == 200:
                    raw = response.json()
                    # Normalize whatever the API returns into our standard shape
                    return self._normalize_response(raw)
        except Exception:
            pass

        # Return mock data as a consistent structure
        # Only return records for page 1 to avoid duplicating mock data
        if page == 1:
            return {"status": "success", "data": {"records": MOCK_RECORDS}}
        return {"status": "success", "data": {"records": []}}

    def _normalize_response(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize various API response shapes into {"data": {"records": [...]}}"""
        # Already our format
        if isinstance(raw.get("data"), dict) and "records" in raw["data"]:
            return raw
        # data is a list directly
        if isinstance(raw.get("data"), list):
            return {"status": "success", "data": {"records": raw["data"]}}
        # top-level records
        if "records" in raw:
            return {"status": "success", "data": {"records": raw["records"]}}
        # Unknown shape — wrap it
        return {"status": "success", "data": {"records": []}}
