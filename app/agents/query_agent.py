import os
import re
import json
from typing import Dict, Any, Optional

from app.services.food_knowledge_service import FoodKnowledgeService
from app.tools.google_maps_tool import GoogleMapsTool

try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel

    class QueryIntent(BaseModel):
        action: str 
        food: Optional[str] = None
        location: Optional[str] = None
        place_type: Optional[str] = None

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    QueryIntent = None

class QueryAgent:
    def __init__(self, knowledge_service: FoodKnowledgeService):
        self.knowledge = knowledge_service
        self.maps_tool = GoogleMapsTool()

    def _fallback_intent(self, query: str) -> dict:
        q = query.lower()
        
        # 1. Price Intent (Strict routing to Agmarknet)
        if any(w in q for w in ["price", "cost", "agmarknet", "market price", "how much", "rate"]):
            words = query.replace("?", "").split()
            # Try to grab the food name (ignore small words)
            food = next((w for w in reversed(words) if len(w) > 3 and w not in ["price", "cost", "much", "rate", "today"]), words[-1] if words else "")
            return {"action": "agmarknet_price", "food": food, "location": None, "place_type": None}

        # 2. Maps Intent
        for place in ["hospital", "pharmacy", "clinic"]:
            if place in q:
                loc = q.split(" in ")[-1].replace("?", "").strip().title() if " in " in q else None
                return {"action": "maps_search", "food": None, "location": loc, "place_type": place}
        
        # 3. Default: Safety Intent
        match = re.search(r"(?:eat|avoid)\s+(.+?)(?:\s+in\s+(.+?))?(?:\?|$)", query, re.IGNORECASE)
        food = match.group(1).strip() if match else query.replace("?", "").strip()
        location = match.group(2).strip().title() if match and match.group(2) else None
        return {"action": "safety_check", "food": food, "location": location, "place_type": None}

    def _parse_intent(self, query: str) -> dict:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and _GENAI_AVAILABLE and len(query.strip()) >= 10:
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"Classify this query: '{query}'. Fields: action (safety_check, maps_search, agmarknet_price), food, location, place_type. If they ask about cost/price of an agricultural item, use 'agmarknet_price'.",
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=QueryIntent, temperature=0.1),
                )
                if response.text:
                    data = json.loads(response.text)
                    return data
            except Exception:
                pass
        return self._fallback_intent(query)

    async def process_query(self, query: str, user_profile: Dict[str, Any] = None) -> str:
        intent = self._parse_intent(query)
        profile = user_profile or {}
        
        conditions = profile.get("conditions", [])
        allergies = profile.get("allergies", [])
        medications = profile.get("medications", [])

        # ── MAPS SEARCH ──
        if intent.get("action") == "maps_search":
            loc = intent.get("location") or "current location"
            places = self.maps_tool.find_hospitals(loc)
            if places:
                names = [(p.get("name", "Unknown") if isinstance(p, dict) else str(p)) for p in places[:3]]
                return f"Here are hospitals near {loc}:\n\n* " + "\n* ".join(names)
            return f"No locations found near {loc}."

        # ── AGMARKNET PRICE SEARCH (FIVETRAN INTEGRATION) ──
        if intent.get("action") == "agmarknet_price":
            food = (intent.get("food") or "").strip()
            if not food: return "Which commodity's price are you looking for?"
            
            price_info = await self.knowledge.get_price_for_food(food)
            if price_info:
                trend_arrow = {"up": "↑", "down": "↓", "stable": "→"}.get(price_info.trend, "")
                # Format with markdown for UI rendering
                return (
                    f"### 🌾 Live Market Data (Agmarknet via Fivetran)\n"
                    f"**Commodity:** {price_info.commodity.title()}\n"
                    f"**Modal Price:** ₹{price_info.price:,.2f} per quintal {trend_arrow} ({price_info.trend})"
                )
            return f"No live market price found for '{food}' in the Fivetran pipeline. Try searching on agmarknet.gov.in."

        # ── SAFETY CHECK ──
        food = (intent.get("food") or "").strip()
        if not food: return "I couldn't understand what food you're asking about."

        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and _GENAI_AVAILABLE:
            try:
                client = genai.Client(api_key=api_key)
                profile_str = f"Conditions: {', '.join(conditions) if conditions else 'None'} | Allergies: {', '.join(allergies) if allergies else 'None'} | Medications: {', '.join(medications) if medications else 'None'}"
                
                prompt = (
                    f"Analyze the food/dish '{food}'. Act as a strict clinical nutritionist. The user's health profile is: [{profile_str}]\n\n"
                    f"Format your response with proper Markdown (use bolding `**`, headers `###`, and bullet points `*`).\n"
                    f"1. Define the food and its primary ingredients.\n"
                    f"2. Estimate its nutritional value per 100g (focus on carbs, sugar, sodium).\n"
                    f"3. CLINICAL VERDICT: Analyze this food specifically against the user's Conditions, Allergies, and Medications. "
                    f"Be direct, clinical, and highlight critical warnings in bold."
                )
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(temperature=0.2),
                )
                if response.text: return response.text.strip()
            except Exception as e:
                return f"Could not retrieve advanced clinical information for '{food}'. ({e})"

        return f"No local database match found for '{food}', and AI engine is offline."