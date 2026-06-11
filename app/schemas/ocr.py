from pydantic import BaseModel

class OCRResult(BaseModel):
    extracted_text: str
    confidence_score: float