"""
NutriGuard AI — FastAPI Backend
AI-Powered Travel Health Copilot
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=False)

# Strip placeholder values that come from .env.example
_PLACEHOLDERS = {
    "your_gemini_api_key_here", "your_maps_api_key_here",
    "your_fivetran_api_key_here", "your_fivetran_api_secret_here",
    "nutriguard-ai-hackathon",
}
for _key in ["GEMINI_API_KEY", "GOOGLE_MAPS_API_KEY", "FIVETRAN_API_KEY",
             "FIVETRAN_API_SECRET", "GOOGLE_CLOUD_PROJECT"]:
    if os.environ.get(_key, "") in _PLACEHOLDERS:
        os.environ.pop(_key, None)

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List


# ── Request / Response schemas ─────────────────────────────────────────────

class MissionRequest(BaseModel):
    user_id: str = Field(default="anonymous")
    destination: str = Field(..., min_length=2)
    medical_text: Optional[str] = Field(None)
    ocr_text: Optional[str] = Field(None, description="Pre-extracted OCR text from uploaded file")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2)
    destination: Optional[str] = None
    allergies: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1)


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("NutriGuard AI starting up…")
    yield
    print("NutriGuard AI shut down.")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NutriGuard AI",
    description="AI-Powered Travel Health Copilot — Multi-Agent REST API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ───────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "NutriGuard AI",
        "version": "1.0.0",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "maps_configured": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
        "fivetran_configured": bool(os.environ.get("FIVETRAN_API_KEY")),
    }


# ── Mission ────────────────────────────────────────────────────────────────

@app.post("/api/mission", tags=["Agents"])
async def run_mission(req: MissionRequest):
    """
    Execute the full multi-agent travel health mission.
    Accepts either direct medical_text or pre-extracted ocr_text from a file upload.
    """
    try:
        from app.agents.orchestrator import execute_travel_health_mission

        # Prefer ocr_text (from file upload) over medical_text (typed)
        active_text = (req.ocr_text or req.medical_text or "").strip()

        result = await execute_travel_health_mission(
            user_id=req.user_id,
            destination=req.destination,
            metadata={"medical_text": active_text} if active_text else {},
        )
        return result.model_dump()
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Mission failed: {e}")


# ── Medical parse ──────────────────────────────────────────────────────────

@app.post("/api/parse", tags=["Medical"])
async def parse_medical_text(req: ParseRequest):
    """Parse raw medical text to extract conditions, allergies, and medications."""
    try:
        from app.services.medical_parser import parse_medical_text
        return parse_medical_text(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── OCR ────────────────────────────────────────────────────────────────────

_ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp",
    "image/gif", "application/pdf",
}
_EXT_MAP = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif", "pdf": "application/pdf",
}


@app.post("/api/ocr", tags=["Medical"])
async def ocr_medical_report(file: UploadFile = File(...)):
    """
    Perform OCR on an uploaded medical report (PDF, JPG, PNG, WEBP).
    Returns extracted text and a parsed medical profile.
    """
    content_type = file.content_type or ""
    filename = file.filename or "upload"

    # Infer MIME from extension if generic
    if content_type in ("application/octet-stream", ""):
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        content_type = _EXT_MAP.get(ext, "image/jpeg")

    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Upload JPG, PNG, WEBP, or PDF.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large — maximum 10 MB.")

    try:
        from app.tools.medical_ocr import perform_medical_ocr
        from app.services.medical_parser import parse_medical_text

        ocr_result = await perform_medical_ocr(file_bytes)
        parsed = parse_medical_text(ocr_result.extracted_text) if ocr_result.extracted_text else {
            "conditions": [], "allergies": [], "medications": [], "risk_level": "Low"
        }

        return {
            "extracted_text": ocr_result.extracted_text,
            "confidence_score": ocr_result.confidence_score,
            "parsed_profile": parsed,
            "filename": filename,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")


# ── Query Agent ────────────────────────────────────────────────────────────

@app.post("/api/query", tags=["Agents"])
async def run_query(req: QueryRequest):
    """Process a natural language health/food/travel query."""
    try:
        from app.repositories import (
            IFCTRepository, DrugRepository, CuisineRepository, USDARepository
        )
        from app.services.food_knowledge_service import FoodKnowledgeService
        from app.agents.query_agent import QueryAgent

        service = FoodKnowledgeService(
            IFCTRepository(), DrugRepository(), CuisineRepository(), USDARepository()
        )
        agent = QueryAgent(service)
        response = await agent.process_query(
            req.query,
            {"allergies": req.allergies or [], "medications": req.medications or []},
        )
        return {"response": response, "query": req.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Live prices ────────────────────────────────────────────────────────────

@app.get("/api/prices", tags=["Market Data"])
async def get_live_prices():
    """Live commodity prices from Agmarknet via Fivetran pipeline."""
    try:
        from app.tools.agmarknet_tool import AgmarknetTool
        from app.repositories.agmarknet_repository import AgmarknetRepository

        repo = AgmarknetRepository(AgmarknetTool())
        prices = await repo.get_live_prices()
        return {
            "count": len(prices),
            "prices": [p.model_dump() for p in prices[:20]],
            "source": "Agmarknet via Fivetran Pipeline",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Fivetran pipeline status ───────────────────────────────────────────────

@app.get("/api/pipeline", tags=["Infrastructure"])
async def get_pipeline_status():
    """Fivetran data pipeline status."""
    try:
        from app.tools.fivetran_tool import FivetranTool
        return FivetranTool().get_pipeline_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Destination info ───────────────────────────────────────────────────────

@app.get("/api/destination/{destination}", tags=["Travel"])
async def get_destination_info(destination: str):
    """Normalize a destination and return country/cuisine/language."""
    from app.services.destination_normalizer import normalize_destination
    return normalize_destination(destination)


# ── Serve frontend ─────────────────────────────────────────────────────────

_frontend = _project_root / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend / "index.html"))
