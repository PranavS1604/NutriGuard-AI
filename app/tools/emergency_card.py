import os
from app.schemas.emergency_card import EmergencyCardResult

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

async def generate_emergency_card(user_id: str, medical_risks: list, food_allergies: list, destination_language: str) -> EmergencyCardResult:
    """
    Generates a localized multi-lingual waiter or emergency card using Gemini.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    translated_text = "I have strict dietary requirements. Please ensure no cross-contamination."
    
    if api_key and genai and destination_language:
        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"Translate the following medical and allergy warnings into {destination_language} "
                f"(the language of the destination) so I can show it to a waiter or doctor.\n\n"
                f"Conditions: {', '.join(medical_risks)}\n"
                f"Allergies to strictly avoid: {', '.join(food_allergies)}\n\n"
                f"Provide ONLY the translated text, making it clear and polite."
            )
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            if response.text:
                translated_text = response.text.strip()
        except Exception as e:
            print(f"Gemini translation failed: {e}")
            
    # Mock URL generation logic
    lang_code = destination_language.lower()[:2] if destination_language else "en"
    
    return EmergencyCardResult(
        card_url=f"https://mock-url.nutriguard.ai/cards/waiter_card_{lang_code}.png",
        qr_code_url="",
        translated_text=translated_text
    )
