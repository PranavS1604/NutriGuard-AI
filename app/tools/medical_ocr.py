import os
import base64
from app.schemas.ocr import OCRResult

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

_MAGIC_BYTES = {
    b"%PDF": "application/pdf",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
    b"RIFF": "image/webp",
    b"GIF8": "image/gif",
}

def _detect_mime(data: bytes) -> str:
    for magic, mime in _MAGIC_BYTES.items():
        if data[: len(magic)] == magic:
            return mime
    return "image/jpeg"

async def perform_medical_ocr(file_bytes: bytes) -> OCRResult:
    if not file_bytes:
        return OCRResult(extracted_text="", confidence_score=0.0)

    try:
        decoded = file_bytes.decode("utf-8")
        if not decoded.startswith("%PDF") and len(decoded) < 50_000:
            return OCRResult(extracted_text=decoded, confidence_score=0.99)
    except UnicodeDecodeError:
        pass 

    api_key = os.environ.get("GEMINI_API_KEY")
    samba_api_key = os.environ.get("SAMBANOVA_API_KEY")
    mime_type = _detect_mime(file_bytes)

    if api_key and _GENAI_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)
            document_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    document_part,
                    ("You are a medical document OCR system. Extract ALL text from this document exactly "
                     "as it appears — do not summarise, interpret, or omit anything. "
                     "Return only the raw extracted text.")
                ],
            )
            extracted = (response.text or "").strip()
            if extracted:
                return OCRResult(extracted_text=extracted, confidence_score=0.95)
        except Exception as e:
            print(f"[OCR] Gemini failed: {e}")

    if samba_api_key and _SAMBA_AVAILABLE and "image" in mime_type:
        try:
            client = SambaNova(api_key=samba_api_key, base_url="https://api.sambanova.ai/v1")
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            response = client.chat.completions.create(
                model="gemma-4-31B-it",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this medical document exactly as it appears."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                    ]
                }]
            )
            if response.choices[0].message.content:
                return OCRResult(extracted_text=response.choices[0].message.content.strip(), confidence_score=0.90)
        except Exception as e:
            print(f"[OCR] SambaNova failed: {e}")

    return OCRResult(extracted_text=f"(OCR failed. APIs exhausted or invalid format)", confidence_score=0.0)