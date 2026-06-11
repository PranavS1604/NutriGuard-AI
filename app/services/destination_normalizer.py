"""
destination_normalizer.py — Maps city/country names to country, cuisine, and language metadata.
Covers 60+ destinations. Uses Gemini LLM as fallback for unknown destinations.
"""
import os

DESTINATION_MAP = {
    # Japan
    "tokyo": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "osaka": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "kyoto": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "hokkaido": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "okinawa": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "hiroshima": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "nagoya": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},
    "japan": {"country": "Japan", "cuisine": "Japanese", "language": "ja"},

    # India
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
    "india": {"country": "India", "cuisine": "Indian", "language": "hi"},

    # France
    "paris": {"country": "France", "cuisine": "French", "language": "fr"},
    "lyon": {"country": "France", "cuisine": "French", "language": "fr"},
    "nice": {"country": "France", "cuisine": "French", "language": "fr"},
    "marseille": {"country": "France", "cuisine": "French", "language": "fr"},
    "bordeaux": {"country": "France", "cuisine": "French", "language": "fr"},
    "france": {"country": "France", "cuisine": "French", "language": "fr"},

    # Italy
    "rome": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "florence": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "venice": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "milan": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "naples": {"country": "Italy", "cuisine": "Italian", "language": "it"},
    "italy": {"country": "Italy", "cuisine": "Italian", "language": "it"},

    # Mexico
    "mexico city": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},
    "cancun": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},
    "guadalajara": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},
    "mexico": {"country": "Mexico", "cuisine": "Mexican", "language": "es"},

    # Thailand
    "bangkok": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "phuket": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "chiang mai": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "pattaya": {"country": "Thailand", "cuisine": "Thai", "language": "th"},
    "thailand": {"country": "Thailand", "cuisine": "Thai", "language": "th"},

    # South Korea
    "seoul": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "busan": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "incheon": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "korea": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},
    "south korea": {"country": "South Korea", "cuisine": "Korean", "language": "ko"},

    # USA
    "new york": {"country": "United States", "cuisine": "American", "language": "en"},
    "los angeles": {"country": "United States", "cuisine": "American", "language": "en"},
    "chicago": {"country": "United States", "cuisine": "American", "language": "en"},
    "san francisco": {"country": "United States", "cuisine": "American", "language": "en"},
    "miami": {"country": "United States", "cuisine": "American", "language": "en"},
    "las vegas": {"country": "United States", "cuisine": "American", "language": "en"},
    "usa": {"country": "United States", "cuisine": "American", "language": "en"},
    "united states": {"country": "United States", "cuisine": "American", "language": "en"},
    "america": {"country": "United States", "cuisine": "American", "language": "en"},

    # UK
    "london": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "manchester": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "edinburgh": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "uk": {"country": "United Kingdom", "cuisine": "British", "language": "en"},
    "england": {"country": "United Kingdom", "cuisine": "British", "language": "en"},

    # China
    "beijing": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "shanghai": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "shenzhen": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "guangzhou": {"country": "China", "cuisine": "Chinese", "language": "zh"},
    "china": {"country": "China", "cuisine": "Chinese", "language": "zh"},

    # Germany
    "berlin": {"country": "Germany", "cuisine": "German", "language": "de"},
    "munich": {"country": "Germany", "cuisine": "German", "language": "de"},
    "hamburg": {"country": "Germany", "cuisine": "German", "language": "de"},
    "frankfurt": {"country": "Germany", "cuisine": "German", "language": "de"},
    "germany": {"country": "Germany", "cuisine": "German", "language": "de"},

    # Spain
    "madrid": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "barcelona": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "seville": {"country": "Spain", "cuisine": "Spanish", "language": "es"},
    "spain": {"country": "Spain", "cuisine": "Spanish", "language": "es"},

    # Australia
    "sydney": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "melbourne": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "brisbane": {"country": "Australia", "cuisine": "Australian", "language": "en"},
    "australia": {"country": "Australia", "cuisine": "Australian", "language": "en"},

    # UAE / Middle East
    "dubai": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},
    "abu dhabi": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},
    "uae": {"country": "United Arab Emirates", "cuisine": "Middle Eastern", "language": "ar"},

    # Singapore
    "singapore": {"country": "Singapore", "cuisine": "Singaporean", "language": "en"},

    # Vietnam
    "ho chi minh city": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},
    "hanoi": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},
    "vietnam": {"country": "Vietnam", "cuisine": "Vietnamese", "language": "vi"},

    # Indonesia / Bali
    "bali": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},
    "jakarta": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},
    "indonesia": {"country": "Indonesia", "cuisine": "Indonesian", "language": "id"},

    # Brazil
    "rio de janeiro": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},
    "sao paulo": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},
    "brazil": {"country": "Brazil", "cuisine": "Brazilian", "language": "pt"},

    # Greece
    "athens": {"country": "Greece", "cuisine": "Greek", "language": "el"},
    "santorini": {"country": "Greece", "cuisine": "Greek", "language": "el"},
    "greece": {"country": "Greece", "cuisine": "Greek", "language": "el"},

    # Turkey
    "istanbul": {"country": "Turkey", "cuisine": "Turkish", "language": "tr"},
    "ankara": {"country": "Turkey", "cuisine": "Turkish", "language": "tr"},
    "turkey": {"country": "Turkey", "cuisine": "Turkish", "language": "tr"},

    # Morocco
    "marrakech": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},
    "casablanca": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},
    "morocco": {"country": "Morocco", "cuisine": "Moroccan", "language": "ar"},

    # Canada
    "toronto": {"country": "Canada", "cuisine": "Canadian", "language": "en"},
    "vancouver": {"country": "Canada", "cuisine": "Canadian", "language": "en"},
    "montreal": {"country": "Canada", "cuisine": "Canadian", "language": "fr"},
    "canada": {"country": "Canada", "cuisine": "Canadian", "language": "en"},

    # Portugal
    "lisbon": {"country": "Portugal", "cuisine": "Portuguese", "language": "pt"},
    "porto": {"country": "Portugal", "cuisine": "Portuguese", "language": "pt"},
    "portugal": {"country": "Portugal", "cuisine": "Portuguese", "language": "pt"},

    # Switzerland
    "zurich": {"country": "Switzerland", "cuisine": "Swiss", "language": "de"},
    "geneva": {"country": "Switzerland", "cuisine": "Swiss", "language": "fr"},
    "switzerland": {"country": "Switzerland", "cuisine": "Swiss", "language": "de"},

    # Netherlands
    "amsterdam": {"country": "Netherlands", "cuisine": "Dutch", "language": "nl"},
    "netherlands": {"country": "Netherlands", "cuisine": "Dutch", "language": "nl"},

    # Malaysia
    "kuala lumpur": {"country": "Malaysia", "cuisine": "Malaysian", "language": "ms"},
    "malaysia": {"country": "Malaysia", "cuisine": "Malaysian", "language": "ms"},

    # Philippines
    "manila": {"country": "Philippines", "cuisine": "Filipino", "language": "tl"},
    "philippines": {"country": "Philippines", "cuisine": "Filipino", "language": "tl"},

    # Argentina
    "buenos aires": {"country": "Argentina", "cuisine": "Argentine", "language": "es"},
    "argentina": {"country": "Argentina", "cuisine": "Argentine", "language": "es"},
}


def normalize_destination(destination: str) -> dict:
    """
    Normalizes a destination name into country, cuisine, and language code.
    First checks the built-in map; if not found, tries Gemini LLM for intelligent resolution.
    Falls back to using the input as-is with English language.
    """
    if not destination:
        return {"country": "Unknown", "cuisine": "Unknown", "language": "en"}

    dest_lower = destination.lower().strip()

    # Check exact map match first
    if dest_lower in DESTINATION_MAP:
        return DESTINATION_MAP[dest_lower]

    # Try partial matches (e.g., user typed "New York City")
    for key, value in DESTINATION_MAP.items():
        if key in dest_lower or dest_lower in key:
            return value

    # Try Gemini for unknown destinations
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types
            from pydantic import BaseModel

            class DestinationInfo(BaseModel):
                country: str
                cuisine: str
                language: str  # ISO 639-1 two-letter code

            client = genai.Client(api_key=api_key)
            prompt = (
                f"For the travel destination '{destination}', provide:\n"
                f"1. The country name (in English)\n"
                f"2. The primary local cuisine type (e.g. Japanese, Italian, Indian)\n"
                f"3. The ISO 639-1 two-letter language code (e.g. ja, it, hi)\n"
                f"Respond with only JSON."
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DestinationInfo,
                    temperature=0.1
                )
            )
            if response.text:
                import json
                data = json.loads(response.text)
                return {
                    "country": data.get("country", destination.title()),
                    "cuisine": data.get("cuisine", destination.title()),
                    "language": data.get("language", "en")
                }
        except Exception as e:
            print(f"Gemini destination resolution failed: {e}")

    # Final fallback — use input as-is
    return {
        "country": destination.title(),
        "cuisine": destination.title(),
        "language": "en"
    }
