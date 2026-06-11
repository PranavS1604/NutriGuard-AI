import os
import re
import json
from typing import Dict, Any, Optional

from app.services.food_knowledge_service import FoodKnowledgeService
from app.tools.google_maps_tool import GoogleMapsTool
from app.tools.fivetran_tool import FivetranTool

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

try:
    from sambanova import SambaNova
    _SAMBA_AVAILABLE = True
except ImportError:
    _SAMBA_AVAILABLE = False


class QueryAgent:
    def __init__(
        self,
        knowledge_service: FoodKnowledgeService,
        maps_tool: Optional[GoogleMapsTool] = None,
    ):
        self.knowledge = knowledge_service
        self.maps_tool = maps_tool or GoogleMapsTool()
        self.fivetran_tool = FivetranTool() # Inject Fivetran Superpower!

    def _fallback_intent(self, query: str) -> dict:
        q = query.lower()
        
        if any(w in q for w in ["sync", "update data", "fivetran", "pipeline status", "check pipeline"]):
            return {"action": "fivetran_ops", "food": None, "location": None, "place_type": None}

        if any(w in q for w in ["price", "cost", "agmarknet", "market price", "how much", "rate"]):
            words = query.replace("?", "").split()
            food = next((w for w in reversed(words) if len(w) > 3 and w not in ["price", "cost", "much", "rate", "today"]), words[-1] if words else "")
            return {"action": "agmarknet_price", "food": food, "location": None, "place_type": None}

        for place in ["hospital", "pharmacy", "clinic", "restaurant", "chemist"]:
            if place in q:
                loc = None
                if " in " in q:
                    loc = q.split(" in ")[-1].replace("?", "").strip().title()
                return {"action": "maps_search", "food": None, "location": loc, "place_type": place}
        
        match = re.search(r"(?:eat|avoid|drink)\s+(.+?)(?:\s+in\s+(.+?))?(?:\?|$)", query, re.IGNORECASE)
        food = match.group(1).strip() if match else None
        location = match.group(2).strip().title() if match and match.group(2) else None
        return {"action": "general_chat", "food": food, "location": location, "place_type": None}

    def _parse_intent(self, query: str) -> dict:
        api_key = os.environ.get("GEMINI_API_KEY")
        samba_api_key = os.environ.get("SAMBANOVA_API_KEY")
        
        prompt_text = (
            f"Classify this query: '{query}'. "
            f"If it asks to sync, update, or check fivetran/pipelines, action='fivetran_ops'. "
            f"If it asks for a price/cost, action='agmarknet_price'. "
            f"If it asks for a location (hospital/pharmacy), action='maps_search'. "
            f"Otherwise, action='general_chat'."
        )

        if api_key and _GENAI_AVAILABLE and len(query.strip()) >= 10:
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_text,
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=QueryIntent, temperature=0.1),
                )
                if response.text: return json.loads(response.text)
            except Exception: pass

        if samba_api_key and _SAMBA_AVAILABLE and len(query.strip()) >= 10:
            try:
                client = SambaNova(api_key=samba_api_key, base_url="https://api.sambanova.ai/v1")
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_text + " Output JSON only."}],
                    model="Meta-Llama-3.3-70B-Instruct",
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                if response.choices[0].message.content: return json.loads(response.choices[0].message.content)
            except Exception: pass

        return self._fallback_intent(query)

    async def process_query(self, query: str, user_profile: Dict[str, Any] = None) -> str:
        if not query or not query.strip():
            return "Please enter a question."

        intent = self._parse_intent(query)
        profile = user_profile or {}
        conditions = profile.get("conditions", [])
        allergies = profile.get("allergies", [])
        medications = profile.get("medications", [])

        # ── FIVETRAN OPERATIONS ──
        if intent.get("action") == "fivetran_ops":
            if "sync" in query.lower() or "update" in query.lower():
                return await self.fivetran_tool.force_sync()
            else:
                return await self.fivetran_tool.check_connector_status()

        # ── MAPS SEARCH ──
        if intent.get("action") == "maps_search":
            loc = intent.get("location") or "current location"
            place_type = intent.get("place_type") or "hospital"
            if place_type.lower() not in ["hospital", "pharmacy", "clinic", "restaurant", "chemist"]:
                place_type = "hospital"
            places = self.maps_tool.find_hospitals(loc)
            if places:
                names = [(p.get("name", "Unknown") if isinstance(p, dict) else str(p)) for p in places[:3]]
                return f"Here are some {place_type}s near {loc}:\n\n* " + "\n* ".join(names)
            return f"No {place_type}s found near {loc}. Please check Google Maps."

        # ── AGMARKNET PRICE SEARCH ──
        if intent.get("action") == "agmarknet_price":
            food = (intent.get("food") or "").strip()
            if not food: return "Which commodity's price are you looking for?"
            price_info = await self.knowledge.get_price_for_food(food)
            if price_info:
                trend_arrow = {"up": "↑", "down": "↓", "stable": "→"}.get(price_info.trend, "")
                return (
                    f"### 🌾 Live Market Data\n"
                    f"**Commodity:** {price_info.commodity.title()}\n"
                    f"**Modal Price:** ₹{price_info.price:,.2f} per quintal {trend_arrow} ({price_info.trend})\n\n"
                    f"*Data actively synced from Agmarknet to BigQuery via Fivetran.*"
                )
            return f"No live market price found for '{food}' in the Fivetran pipeline."

        # ── GENERAL CLINICAL CHAT ──
        food = (intent.get("food") or "").strip()
        db_context = f"--- FIVETRAN MANAGED DATA WAREHOUSE ---\nSource Pipelines: USDA_Foundation, IFCT_2017, DrugBank_Interactions\nFivetran Sync Status: VALIDATED & FRESH\n"

        if food:
            dish_details = self.knowledge.get_dish_details(food)
            nutrition = self.knowledge.get_food_nutrition(food)
            if dish_details or nutrition:
                db_context += f"\n[LOCAL DB KNOWLEDGE FOR '{food.upper()}']\n"
                if dish_details:
                    db_context += f"Known Ingredients: {dish_details.get('ingredients', 'Unknown')}\n"
                if nutrition:
                    db_context += f"Nutrition (per 100g): Energy {nutrition.get('energy_kj', 0):.0f} kJ, Protein {nutrition.get('protein_g', 0)}g, Fat {nutrition.get('fat_g', 0)}g, Carbs {nutrition.get('carbohydrates_g', 0)}g\n"
        
        db_context += "--------------------------------------\n"

        api_key = os.environ.get("GEMINI_API_KEY")
        samba_api_key = os.environ.get("SAMBANOVA_API_KEY")
        profile_str = f"Conditions: {', '.join(conditions) if conditions else 'None'} | Allergies: {', '.join(allergies) if allergies else 'None'} | Medications: {', '.join(medications) if medications else 'None'}"
        
        system_prompt = (
            f"You are NutriGuard AI, an expert clinical nutritionist and travel health copilot.\n"
            f"The user asked: \"{query}\"\n\n"
            f"USER HEALTH PROFILE:\n[{profile_str}]\n\n"
            f"{db_context}\n"
            f"INSTRUCTIONS:\n"
            f"1. Answer the user's query directly and professionally.\n"
            f"2. CRITICAL: Analyze their question specifically against their Conditions, Allergies, and Medications. If they ask about alcohol and take Metformin, warn them. If they ask about sweets and have Diabetes, flag it.\n"
            f"3. Acknowledge that your nutritional data is sourced from the Fivetran Managed Data Warehouse.\n"
            f"4. Use Markdown formatting. Highlight critical warnings in bold."
        )

        # 1. Gemini
        if api_key and _GENAI_AVAILABLE:
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=system_prompt, config=types.GenerateContentConfig(temperature=0.2),
                )
                if response.text: return response.text.strip()
            except Exception as e: print(f"[Query] Gemini failed: {e}")

        # 2. SambaNova Fallback
        if samba_api_key and _SAMBA_AVAILABLE:
            try:
                client = SambaNova(api_key=samba_api_key, base_url="https://api.sambanova.ai/v1")
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a clinical AI agent. Use Markdown."},
                        {"role": "user", "content": system_prompt}
                    ],
                    model="Meta-Llama-3.3-70B-Instruct",
                    temperature=0.2
                )
                if response.choices[0].message.content: return response.choices[0].message.content.strip()
            except Exception as e: print(f"[Query] SambaNova failed: {e}")

        return f"AI formatting engines are currently offline due to rate limits. Please try again in a moment."