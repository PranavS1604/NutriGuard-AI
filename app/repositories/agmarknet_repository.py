from typing import List, Dict, Any, Optional
from app.tools.agmarknet_tool import AgmarknetTool
from app.schemas.food_price import FoodPrice

FOOD_ALIASES = {
    "bajra": "Bajra(Pearl Millet/Cumbu)",
    "pearl millet": "Bajra(Pearl Millet/Cumbu)",
    "groundnut": "Groundnut",
    "peanut": "Groundnut",
    "peanuts": "Groundnut",
    "maize": "Maize",
    "corn": "Maize",
    "maze": "Maize", # FIXED: Added typo alias
    "wheat": "Wheat",
    "bengal gram": "Bengal Gram(Gram)",
    "chana": "Bengal Gram(Gram)",
    "jowar": "Jowar(Sorghum)",
    "sorghum": "Jowar(Sorghum)",
    "ragi": "Ragi(Finger Millet)"
}

class AgmarknetRepository:
    def __init__(self, tool: AgmarknetTool):
        self.tool = tool
        self._cache = None

    async def get_live_prices(self) -> List[FoodPrice]:
        if self._cache is not None:
            return self._cache

        all_records = []
        for page in [1, 2, 3]:
            data = await self.tool.get_dashboard(page=page)
            records = data.get("records", [])
            if not records:
                break
            all_records.extend(records)
            
        seen = set()
        unique_records = []
        for record in all_records:
            commodity = record.get("cmdt_name") or record.get("commodity")
            market = record.get("mkt_name") or record.get("market") or "Unknown"
            
            if not commodity:
                continue
                
            key = (commodity, market)
            if key not in seen:
                seen.add(key)
                unique_records.append(record)

        price_list = []
        for record in unique_records:
            commodity = record.get("cmdt_name") or record.get("commodity")
            price = record.get("as_on_price") or record.get("modal_price") or record.get("price") or 0.0
            trend = record.get("trend", "stable")
            
            if commodity and price is not None:
                try:
                    price_list.append(FoodPrice(
                        commodity=commodity,
                        price=float(str(price).replace(",", "")),
                        trend=trend
                    ))
                except (ValueError, TypeError):
                    pass
                    
        self._cache = price_list
        return price_list

    async def get_price_for_food(self, food: str) -> Optional[FoodPrice]:
        food_lower = food.lower().strip()
        prices = await self.get_live_prices()
        
        target = FOOD_ALIASES.get(food_lower, food_lower)
        for fp in prices:
            if fp.commodity.lower() == target.lower():
                return fp
                
        for fp in prices:
            if target.lower() in fp.commodity.lower() or fp.commodity.lower() in target.lower():
                return fp
                
        return None