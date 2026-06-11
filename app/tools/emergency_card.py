import os
from app.schemas.emergency_card import EmergencyCardResult

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

try:
    from sambanova import SambaNova
    _SAMBA_AVAILABLE = True
except ImportError:
    _SAMBA_AVAILABLE = False

_LANG_NAMES = {
    "ja": "Japanese", "hi": "Hindi", "fr": "French", "it": "Italian",
    "es": "Spanish", "th": "Thai", "ko": "Korean", "zh": "Mandarin Chinese",
    "de": "German", "ar": "Arabic", "pt": "Portuguese", "vi": "Vietnamese",
    "id": "Indonesian", "nl": "Dutch", "el": "Greek", "tr": "Turkish",
    "ms": "Malay", "tl": "Filipino", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "en": "English",
}

_ENGLISH_CARD = (
    "⚠️ MEDICAL ALERT\n\n"
    "I have the following medical conditions and dietary restrictions. "
    "Please ensure my food is prepared accordingly and inform the chef.\n\n"
    "{conditions_section}"
    "{allergies_section}"
    "{medications_section}"
    "In case of emergency, please call local emergency services immediately.\n"
    "Thank you for your understanding."
)


async def generate_emergency_card(
    user_id: str,
    medical_risks: list,
    food_allergies: list,
    destination_language: str,
) -> EmergencyCardResult:
    lang_code = (destination_language or "en").lower()[:2]
    lang_name = _LANG_NAMES.get(lang_code, lang_code.upper())

    conditions_section = (
        f"Medical conditions: {', '.join(medical_risks)}\n" if medical_risks else ""
    )
    allergies_section = (
        f"Strict allergies — MUST NOT consume: {', '.join(food_allergies)}\n"
        if food_allergies
        else ""
    )
    medications_section = "" 

    english_text = _ENGLISH_CARD.format(
        conditions_section=conditions_section,
        allergies_section=allergies_section,
        medications_section=medications_section,
    ).strip()

    translated_text = english_text 

    api_key = os.environ.get("GEMINI_API_KEY")
    samba_api_key = os.environ.get("SAMBANOVA_API_KEY")
    
    prompt = f"Translate the following medical alert card into {lang_name}. Output ONLY the translated text:\n\n{english_text}"

    # 1. Gemini
    if lang_code != "en" and api_key and _GENAI_AVAILABLE and (medical_risks or food_allergies):
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if response.text and response.text.strip():
                return EmergencyCardResult(card_url="", qr_code_url="", translated_text=response.text.strip())
        except Exception as e:
            print(f"[EmergencyCard] Translation failed: {e}")

    # 2. SambaNova Fallback
    if lang_code != "en" and samba_api_key and _SAMBA_AVAILABLE and (medical_risks or food_allergies):
        try:
            client = SambaNova(api_key=samba_api_key, base_url="https://api.sambanova.ai/v1")
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], model="Meta-Llama-3.3-70B-Instruct"
            )
            if response.choices[0].message.content:
                return EmergencyCardResult(card_url="", qr_code_url="", translated_text=response.choices[0].message.content.strip())
        except Exception: 
            pass

    return EmergencyCardResult(
        card_url="", 
        qr_code_url="",
        translated_text=translated_text,
    )