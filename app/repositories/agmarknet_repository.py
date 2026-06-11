from typing import List, Dict, Any, Optional
from app.tools.agmarknet_tool import AgmarknetTool
from app.schemas.food_price import FoodPrice

FOOD_ALIASES = {
    "bajra": "Bajra(Pearl Millet/Cumbu)",
    "pearl millet": "Bajra(Pearl Millet/Cumbu)",
    "groundnut": "Groundnut",
    "peanut": "Groundnut",
    "maize": "Maize",
    "corn": "Maize",
    "wheat": "Wheat",
    "bengal gram": "Bengal Gram(Gram)",
    "chana": "Bengal Gram(Gram)",
    "gram": "Bengal Gram(Gram)"
}

class AgmarknetRepository:
    def __init__(self, tool: AgmarknetTool):
        self.tool = tool

    async def get_live_prices(self) -> List[FoodPrice]:
        """
        Retrieves all live food commodity prices from Agmarknet across multiple pages.
        """
        all_records = []
        for page in [1, 2, 3]:
            data = await self.tool.get_dashboard(page=page)
            # Determine the response data structure (live API vs fallback)
            records = []
            if isinstance(data, dict):
                inner_data = data.get("data")
                if isinstance(inner_data, dict):
                    records = inner_data.get("records", [])
                elif isinstance(inner_data, list):
                    records = inner_data
                else:
                    records = data.get("records", [])
            elif isinstance(data, list):
                records = data
            
            if records:
                all_records.extend(records)
            
        # De-duplicate records based on key composite fields
        # Support both old fallback field names and real Agmarknet API field names
        seen = set()
        unique_records = []
        for record in all_records:
            key = (
                record.get("commodity") or record.get("cmdt_name") or record.get("COMMODITY"),
                record.get("market") or record.get("mkt_name") or record.get("MARKET_NAME"),
                record.get("state") or record.get("state_name") or record.get("STATE"),
                record.get("district") or record.get("dist_name") or record.get("DISTRICT")
            )
            if key not in seen:
                seen.add(key)
                unique_records.append(record)

        price_list = []
        for record in unique_records:
            # Support both fallback and real Agmarknet API field names
            commodity = (
                record.get("commodity") or record.get("cmdt_name")
                or record.get("COMMODITY") or record.get("Commodity")
            )
            price = (
                record.get("modal_price") or record.get("as_on_price")
                or record.get("MODAL_PRICE") or record.get("price") or 0.0
            )
            trend = record.get("trend") or record.get("price_trend") or "stable"
            
            if commodity and price is not None:
                try:
                    price_list.append(FoodPrice(
                        commodity=commodity,
                        price=float(str(price).replace(",", "")),
                        trend=trend
                    ))
                except (ValueError, TypeError):
                    pass  # Skip malformed price records
        return price_list

    async def get_price_for_food(self, food: str) -> Optional[FoodPrice]:
        """
        Retrieves live agricultural price for a specific food item, with alias normalization.
        """
        food_lower = food.lower()
        # Resolve aliases if any
        target_commodity = FOOD_ALIASES.get(food_lower, food_lower)
        
        prices = await self.get_live_prices()
        for fp in prices:
            if fp.commodity.lower() == target_commodity.lower():
                return fp
            # Substring match fallback
            if target_commodity.lower() in fp.commodity.lower():
                return fp
        return None
