"""
destination_normalizer.py
Maps city/country names → {country, cuisine, language}.
Covers 120+ destinations. Uses Gemini as fallback for unknown places.
"""
import os
import json

DESTINATION_MAP: dict = {
    # ── Japan ──────────────────────────────────────────────────────────────
    "japan": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "tokyo": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "osaka": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "kyoto": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "hiroshima": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "nagoya": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "sapporo": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "fukuoka": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "okinawa": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "hokkaido": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},

    # ── India ──────────────────────────────────────────────────────────────
    "india": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "mumbai": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "delhi": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "new delhi": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "bangalore": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "bengaluru": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "chennai": {"country": "India", "cuisine": "Indian", "language": "ta"},
    "kolkata": {"country": "India", "cuisine": "Indian", "language": "bn"},
    "hyderabad": {"country": "India", "cuisine": "Indian", "language": "te"},
    "pune": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "goa": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "jaipur": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "nagpur": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "ahmedabad": {"country": "India", "cuisine": "Indian", "language": "gu"},
    "surat": {"country": "India", "cuisine": "Indian", "language": "gu"},
    "lucknow": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "agra": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "varanasi": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "amritsar": {"country": "India", "cuisine": "Indian", "language": "pa"},
    "kochi": {"country": "India", "cuisine": "Indian", "language": "ml"},
    "coimbatore": {"country": "India", "cuisine": "Indian", "language": "ta"},
    "bhopal": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "indore": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "patna": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "chandigarh": {"country": "India", "cuisine": "Indian", "language": "hi"},
    "visakhapatnam": {"country": "India", "cuisine": "Indian", "language": "te"},
    "bhubaneswar": {"country": "India", "cuisine": "Indian", "language": "or"},

    # ── France ────────────────────────────────────────────────────────────
    "france": {"country": "France", "cuisine": "French", "language": "fr"},
    "paris": {"country": "France", "cuisine": "French", "language": "fr"},
    "lyon": {"country": "France", "cuisine": "French", "language": "fr"},
    "nice": {"country": "France", "cuisine": "French", "language": "fr"},
    "marseille": {"country": "France", "cuisine": "French", "language": "fr"},
    "bordeaux": {"country": "France", "cuisine": "French", "language": "fr"},
    "strasbourg": {"country": "France", "cuisine": "French", "language": "fr"},

    # ── Italy ─────────────────────────────────────────────────────────────
    "italy": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "rome": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "florence": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "venice": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "milan": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "naples": {"country": "Italy", "cuisine": "Italian", "language": "it"},

    # ── Thailand ──────────────────────────────────────────────────────────
    "thailand": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "bangkok": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "phuket": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "chiang mai": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "pattaya": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "koh samui": {"country": "Thailand", "cuisine": "Thai", "language": "th"},

    # ── South Korea ───────────────────────────────────────────────────────
    "korea": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "south korea": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "seoul": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "busan": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "incheon": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "jeju": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},

    # ── USA ───────────────────────────────────────────────────────────────
    "usa": {"country": "United States", "cuisine": "American", "language": "en"},
    "united states": {"country": "United States", "cuisine": "American", "language": "en"},
    "america": {"country": "United States", "cuisine": "American", "language": "en"},
    "new york": {"country": "United States", "cuisine": "American", "language": "en"},
    "los angeles": {"country": "United States", "cuisine": "American", "language": "en"},
    "chicago": {"country": "United States", "cuisine": "American", "language": "en"},
    "san francisco": {"country": "United States", "cuisine": "American", "language": "en"},
    "miami": {"country": "United States", "cuisine": "American", "language": "en"},
    "las vegas": {"country": "United States", "cuisine": "American", "language": "en"},
    "seattle": {"country": "United States", "cuisine": "American", "language": "en"},
    "boston": {"country": "United States", "cuisine": "American", "language": "en"},
    "houston": {"country": "United States", "cuisine": "American", "language": "en"},

    # ── UK ────────────────────────────────────────────────────────────────
    "uk": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "england": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "united kingdom": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "london": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "manchester": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "edinburgh": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "birmingham": {"country": "United Kingdom", "cuisine": "British", "language": "en"},

    # ── China ─────────────────────────────────────────────────────────────
    "china": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "beijing": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "shanghai": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "shenzhen": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "guangzhou": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "chengdu": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "hong kong": {"country": "Hong Kong", "cuisine": "Cantonese", "language": "zh"},

    # ── Germany ───────────────────────────────────────────────────────────
    "germany": {"country": "Germany", "cuisine": "German", "language": "de"},
    "berlin": {"country": "Germany", "cuisine": "German", "language": "de"},
    "munich": {"country": "Germany", "cuisine": "German", "language": "de"},
    "hamburg": {"country": "Germany", "cuisine": "German", "language": "de"},
    "frankfurt": {"country": "Germany", "cuisine": "German", "language": "de"},

    # ── Spain ─────────────────────────────────────────────────────────────
    "spain": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "madrid": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "barcelona": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "seville": {"country": "Spain", "cuisine": "Spanish", "language": "es"},

    # ── Mexico ────────────────────────────────────────────────────────────
    "mexico": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},
    "mexico city": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},
    "cancun": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},

    # ── Australia ─────────────────────────────────────────────────────────
    "australia": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "sydney": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "melbourne": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "brisbane": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "perth": {"country": "Australia", "cuisine": "Australian", "language": "en"},

    # ── UAE ───────────────────────────────────────────────────────────────
    "uae": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},
    "dubai": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},
    "abu dhabi": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},

    # ── Southeast Asia ────────────────────────────────────────────────────
    "singapore": {"country": "Singapore", "cuisine": "Singaporean", "language": "en"},
    "malaysia": {"country": "Malaysia", "cuisine": "Malaysian", "language": "ms"},
    "kuala lumpur": {"country": "Malaysia", "cuisine": "Malaysian", "language": "ms"},
    "vietnam": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},
    "hanoi": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},
    "ho chi minh city": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},
    "indonesia": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},
    "jakarta": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},
    "bali": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},
    "philippines": {"country": "Philippines", "cuisine": "Filipino", "language": "tl"},
    "manila": {"country": "Philippines", "cuisine": "Filipino", "language": "tl"},

    # ── Middle East / Africa ──────────────────────────────────────────────
    "turkey": {"country": "Turkey", "cuisine": "Turkish", "language": "tr"},
    "istanbul": {"country": "Turkey", "cuisine": "Turkish", "language": "tr"},
    "morocco": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},
    "marrakech": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},
    "casablanca": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},
    "egypt": {"country": "Egypt", "cuisine": "Egyptian", "language": "ar"},
    "cairo": {"country": "Egypt", "cuisine": "Egyptian", "language": "ar"},
    "israel": {"country": "Israel", "cuisine": "Israeli", "language": "he"},
    "tel aviv": {"country": "Israel", "cuisine": "Israeli", "language": "he"},
    "saudi arabia": {"country": "Saudi Arabia", "cuisine": "Middle Eastern", "language": "ar"},
    "riyadh": {"country": "Saudi Arabia", "cuisine": "Middle Eastern", "language": "ar"},

    # ── Europe (more) ─────────────────────────────────────────────────────
    "portugal": {"country": "Portugal", "cuisine": "Portuguese", "language": "pt"},
    "lisbon": {"country": "Portugal", "cuisine": "Portuguese", "language": "pt"},
    "netherlands": {"country": "Netherlands", "cuisine": "Dutch", "language": "nl"},
    "amsterdam": {"country": "Netherlands", "cuisine": "Dutch", "language": "nl"},
    "switzerland": {"country": "Switzerland", "cuisine": "Swiss", "language": "de"},
    "zurich": {"country": "Switzerland", "cuisine": "Swiss", "language": "de"},
    "geneva": {"country": "Switzerland", "cuisine": "Swiss", "language": "fr"},
    "greece": {"country": "Greece", "cuisine": "Greek", "language": "el"},
    "athens": {"country": "Greece", "cuisine": "Greek", "language": "el"},
    "santorini": {"country": "Greece", "cuisine": "Greek", "language": "el"},
    "sweden": {"country": "Sweden", "cuisine": "Scandinavian", "language": "sv"},
    "stockholm": {"country": "Sweden", "cuisine": "Scandinavian", "language": "sv"},
    "norway": {"country": "Norway", "cuisine": "Scandinavian", "language": "no"},
    "oslo": {"country": "Norway", "cuisine": "Scandinavian", "language": "no"},
    "denmark": {"country": "Denmark", "cuisine": "Scandinavian", "language": "da"},
    "copenhagen": {"country": "Denmark", "cuisine": "Scandinavian", "language": "da"},
    "austria": {"country": "Austria", "cuisine": "Austrian", "language": "de"},
    "vienna": {"country": "Austria", "cuisine": "Austrian", "language": "de"},
    "poland": {"country": "Poland", "cuisine": "Polish", "language": "pl"},
    "warsaw": {"country": "Poland", "cuisine": "Polish", "language": "pl"},
    "czech republic": {"country": "Czech Republic", "cuisine": "Czech", "language": "cs"},
    "prague": {"country": "Czech Republic", "cuisine": "Czech", "language": "cs"},
    "hungary": {"country": "Hungary", "cuisine": "Hungarian", "language": "hu"},
    "budapest": {"country": "Hungary", "cuisine": "Hungarian", "language": "hu"},
    "russia": {"country": "Russia", "cuisine": "Russian", "language": "ru"},
    "moscow": {"country": "Russia", "cuisine": "Russian", "language": "ru"},

    # ── Americas ──────────────────────────────────────────────────────────
    "canada": {"country": "Canada", "cuisine": "Canadian", "language": "en"},
    "toronto": {"country": "Canada", "cuisine": "Canadian", "language": "en"},
    "vancouver": {"country": "Canada", "cuisine": "Canadian", "language": "en"},
    "montreal": {"country": "Canada", "cuisine": "Canadian", "language": "fr"},
    "brazil": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},
    "sao paulo": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},
    "rio de janeiro": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},
    "argentina": {"country": "Argentina", "cuisine": "Argentine", "language": "es"},
    "buenos aires": {"country": "Argentina", "cuisine": "Argentine", "language": "es"},
    "colombia": {"country": "Colombia", "cuisine": "Colombian", "language": "es"},
    "bogota": {"country": "Colombia", "cuisine": "Colombian", "language": "es"},
    "peru": {"country": "Peru", "cuisine": "Peruvian", "language": "es"},
    "lima": {"country": "Peru", "cuisine": "Peruvian", "language": "es"},

    # ── Other ─────────────────────────────────────────────────────────────
    "new zealand": {"country": "New Zealand", "cuisine": "New Zealand", "language": "en"},
    "auckland": {"country": "New Zealand", "cuisine": "New Zealand", "language": "en"},
    "south africa": {"country": "South Africa", "cuisine": "South African", "language": "en"},
    "cape town": {"country": "South Africa", "cuisine": "South African", "language": "en"},
    "johannesburg": {"country": "South Africa", "cuisine": "South African", "language": "en"},
    "nigeria": {"country": "Nigeria", "cuisine": "Nigerian", "language": "en"},
    "kenya": {"country": "Kenya", "cuisine": "Kenyan", "language": "sw"},
    "nairobi": {"country": "Kenya", "cuisine": "Kenyan", "language": "sw"},
    "ethiopia": {"country": "Ethiopia", "cuisine": "Ethiopian", "language": "am"},
}


def normalize_destination(destination: str) -> dict:
    """
    Normalise a destination string to {country, cuisine, language}.
    Priority: exact map match → partial match → Gemini LLM → raw fallback.
    """
    if not destination or not destination.strip():
        return {"country": "Unknown", "cuisine": "Unknown", "language": "en"}

    key = destination.lower().strip()

    # Exact match
    if key in DESTINATION_MAP:
        return DESTINATION_MAP[key]

    # Partial match (e.g. "New York City" → "new york")
    for map_key, value in DESTINATION_MAP.items():
        if map_key in key or key in map_key:
            return value

    # Gemini fallback for unknown destinations
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types
            from pydantic import BaseModel

            class DestinationInfo(BaseModel):
                country: str
                cuisine: str
                language: str  # ISO 639-1

            client = genai.Client(api_key=api_key)
            prompt = (
                f"For the travel destination '{destination}', provide:\n"
                f"1. The country name in English\n"
                f"2. The primary local cuisine type (e.g. Japanese, Italian)\n"
                f"3. The ISO 639-1 two-letter language code (e.g. ja, it, hi)\n"
                f"Return only JSON."
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DestinationInfo,
                    temperature=0.1,
                ),
            )
            if response.text:
                data = json.loads(response.text)
                return {
                    "country": data.get("country", destination.title()),
                    "cuisine": data.get("cuisine", destination.title()),
                    "language": data.get("language", "en"),
                }
        except Exception as e:
            print(f"[Destination] Gemini resolution failed: {e}")

    # Final fallback
    return {"country": destination.title(), "cuisine": destination.title(), "language": "en"}
