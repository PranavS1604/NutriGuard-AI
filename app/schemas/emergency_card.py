from pydantic import BaseModel

class EmergencyCardResult(BaseModel):
    card_url: str
    qr_code_url: str = ""
    translated_text: str = ""