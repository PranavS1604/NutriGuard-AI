import os
import re
import asyncio
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, Field
from app.services.food_knowledge_service import FoodKnowledgeService
from app.tools.google_maps_tool import GoogleMapsTool

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

class QueryIntent(BaseModel):
    action: str = Field(description="One of: 'safety_check', 'agmarknet_price', 'maps_search', 'unknown'")
    food: Optional[str] = Field(description="The food, dish, or commodity mentioned")
    location: Optional[str] = Field(description="The city or country mentioned")
    place_type: Optional[str] = Field(description="For maps_search: e.g. 'hospital', 'pharmacy', 'restaurant'")

class QueryAgent:
    def __init__(self, knowledge_service: FoodKnowledgeService, maps_tool: Optional[GoogleMapsTool] = None):
        self.knowledge = knowledge_service
        self.maps_tool = maps_tool or GoogleMapsTool()

    def _parse_intent_fallback(self, query: str) -> QueryIntent:
        query_lower = query.lower()
        if "price" in query_lower or "agmarknet" in query_lower:
            food = query.replace("?", "").split()[-1]
            return QueryIntent(action="agmarknet_price", food=food, location=None, place_type=None)
        elif "hospital" in query_lower or "pharmacy" in query_lower or "restaurant" in query_lower:
            place_type = "hospital" if "hospital" in query_lower else "pharmacy" if "pharmacy" in query_lower else "restaurant"
            location = query.split("in ")[-1].replace("?", "").strip() if "in " in query_lower else None
            return QueryIntent(action="maps_search", food=None, location=location, place_type=place_type)
        else:
            match = re.search(r'(?:eat|avoid)\s+(.+?)\s+(?:in|at)\s+(.+?)(?:\?|$)', query, re.IGNORECASE)
            food = match.group(1).strip() if match else query.replace("?", "").strip()
            location = match.group(2).strip() if match else None
            return QueryIntent(action="safety_check", food=food, location=location, place_type=None)

    def _parse_query(self, query: str) -> QueryIntent:
        # Short queries don't need Gemini — use fast regex router
        if len(query.strip()) < 25:
            return self._parse_intent_fallback(query)
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and genai:
            try:
                client = genai.Client(api_key=api_key)
                prompt = f"Analyze the following user query and extract the intent:\n\nQuery: '{query}'"
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=QueryIntent,
                        temperature=0.1
                    )
                )
                if response.text:
                    import json
                    data = json.loads(response.text)
                    return QueryIntent(**data)
            except Exception as e:
                print(f"Gemini intent parsing failed: {e}. Falling back to regex.")
        return self._parse_intent_fallback(query)

    async def process_query(self, query: str, user_profile: Dict[str, Any] = None) -> str:
        intent = self._parse_query(query)
        profile = user_profile or {}
        allergies = profile.get("allergies", [])
        
        if intent.action == "maps_search":
            loc = intent.location or "current location"
            places = []
            if intent.place_type == "hospital":
                places = self.maps_tool.find_hospitals(loc)
            elif intent.place_type == "pharmacy":
                places = self.maps_tool.find_pharmacies(loc)
            else:
                places = self.maps_tool.find_restaurants(loc)
                
            if places:
                names = [p.get('name') for p in places[:3]]
                return f"Here are some {intent.place_type}s near {loc}:\n- " + "\n- ".join(names)
            return f"I couldn't find any {intent.place_type}s near {loc}."

        if intent.action == "agmarknet_price":
            if not intent.food:
                return "Which food or commodity's price are you looking for?"
            price_info = await self.knowledge.get_price_for_food(intent.food)
            if price_info:
                return f"The current modal price for {price_info.commodity} is INR {price_info.price} ({price_info.trend})."
            return f"I couldn't find live market pricing for {intent.food}."

        # Default to safety_check
        food = intent.food
        location = intent.location
        if not food:
            return "I couldn't understand what food you're asking about."

        response = ""
        # 1. Check if it's a known recipe/dish first
        dish_details = self.knowledge.get_dish_details(food)
        if dish_details:
            ingredients = dish_details.get('ingredients', 'Unknown')
            response += f"'{dish_details.get('name')}' is a {dish_details.get('associated_cuisines', 'local')} dish made with: {ingredients}.\n"
            
            # Check allergens against dish ingredients
            dish_allergens = [a for a in allergies if a.lower() in str(ingredients).lower()]
            if dish_allergens:
                response += f"[WARNING] This dish contains ingredients you are allergic to ({', '.join(dish_allergens)})!\n\n"
            else:
                response += f"[SAFE] This dish appears safe for your profile based on common recipes.\n\n"
        else:
            # 2. If location is provided and no specific dish was matched, check location risks
            if location:
                high_risk = self.knowledge.find_high_risk_dishes(location, allergies)
                is_high_risk = any(food.lower() in hr['dish_name'].lower() for hr in high_risk)
                response += f"Checking '{food}' in '{location}'...\n"
                if is_high_risk:
                    response += f"[WARNING] '{food}' may contain ingredients you are allergic to ({', '.join(allergies)})!\n\n"
                else:
                    response += f"[SAFE] '{food}' appears safe for your profile based on common recipes in {location}.\n\n"

        # 3. Get USDA/IFCT food nutrition
        nutrition = self.knowledge.get_food_nutrition(food)
        if nutrition:
            response += f"Nutrition Info ({nutrition['source']}):\n"
            response += f"Energy: {nutrition.get('energy_kj', 0):.0f} kJ\n"
            response += f"Protein: {nutrition.get('protein_g', 0)}g\n"
            response += f"Fat: {nutrition.get('fat_g', 0)}g\n"
            response += f"Carbs: {nutrition.get('carbohydrates_g', 0)}g"
            
        if not dish_details and not nutrition:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key and genai:
                try:
                    client = genai.Client(api_key=api_key)
                    profile_str = f"Allergies: {', '.join(allergies)}" if allergies else "No known allergies"
                    prompt = (
                        f"I am looking for information about the food/dish '{food}'.\n"
                        f"It was not found in my local database. Please act as a food and health safety expert.\n"
                        f"1. Briefly define what this food is and its likely ingredients.\n"
                        f"2. Estimate its nutritional value per 100g.\n"
                        f"3. Perform a safety check against this user profile: {profile_str}\n"
                        f"Respond clearly and concisely."
                    )
                    ai_response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.3
                        )
                    )
                    if ai_response.text:
                        return f"From AI Knowledge Base:\n{ai_response.text.strip()}"
                except Exception as e:
                    return f"I couldn't find any information about '{food}' locally, and the AI fallback failed (Error: {e}). Please try again later."
            return f"I couldn't find any information about '{food}'."
            
        return response.strip()
