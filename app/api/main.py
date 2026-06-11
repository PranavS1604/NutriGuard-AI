"""
NutriGuard AI — FastAPI Backend
AI-Powered Travel Health Copilot — Multi-Agent REST API
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file (local dev only)
# override=False means existing env vars take precedence over .env values
load_dotenv(override=False)

# Filter out placeholder values that were accidentally set from .env.example
_PLACEHOLDER_VALUES = {
    "your_gemini_api_key_here", "your_maps_api_key_here",
    "your_fivetran_api_key_here", "your_fivetran_api_secret_here",
    "nutriguard-ai-hackathon"
}
for _key in ["GEMINI_API_KEY", "GOOGLE_MAPS_API_KEY", "FIVETRAN_API_KEY", "FIVETRAN_API_SECRET", "GOOGLE_CLOUD_PROJECT"]:
    _val = os.environ.get(_key, "")
    if _val in _PLACEHOLDER_VALUES:
        del os.environ[_key]

# Ensure app modules are importable from the project root
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List

# --- Request / Response Schemas ---

class MissionRequest(BaseModel):
    user_id: str = Field(default="anonymous", description="User identifier")
    destination: str = Field(..., description="Travel destination city or country")
    medical_text: Optional[str] = Field(None, description="Raw medical report text for parsing")

class QueryRequest(BaseModel):
    query: str = Field(..., description="Natural language question")
    destination: Optional[str] = Field(None)
    allergies: Optional[List[str]] = Field(default=[])
    medications: Optional[List[str]] = Field(default=[])

class ParseRequest(BaseModel):
    text: str = Field(..., description="Medical report text to parse")

# --- App Lifespan (startup/shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared resources on startup."""
    print("NutriGuard AI API starting up...")
    yield
    print("NutriGuard AI API shutting down.")

# --- FastAPI App ---

app = FastAPI(
    title="NutriGuard AI API",
    description="AI-Powered Travel Health Copilot — Multi-Agent Backend",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS — allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check ---

@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "service": "NutriGuard AI API",
        "version": "1.0.0",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "maps_configured": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
        "fivetran_configured": bool(os.environ.get("FIVETRAN_API_KEY")),
    }

# --- Mission Endpoint ---

@app.post("/api/mission", tags=["Agents"])
async def run_mission(req: MissionRequest):
    """
    Execute a full travel health mission.

    Runs all agents in sequence:
    1. Health Agent (OCR + Medical Profile)
    2. Nutrition Agent (Food Guidelines)
    3. Travel Agent (Destination Risks)
    4. Safety Agent (Drug-Cuisine Engine + Allergens)

    Returns a comprehensive MissionResult.
    """
    try:
        from app.agents.orchestrator import execute_travel_health_mission

        result = await execute_travel_health_mission(
            user_id=req.user_id,
            destination=req.destination,
            metadata={"medical_text": req.medical_text} if req.medical_text else {}
        )

        return result.model_dump()

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Mission failed: {str(e)}")

# --- OCR / Parse Endpoints ---

@app.post("/api/parse", tags=["Medical"])
async def parse_medical_text(req: ParseRequest):
    """
    Parse a medical report text to extract conditions, allergies, and medications.
    Uses Gemini LLM if GEMINI_API_KEY is set, falls back to regex.
    """
    try:
        from app.services.medical_parser import parse_medical_text
        result = parse_medical_text(req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ocr", tags=["Medical"])
async def ocr_medical_report(file: UploadFile = File(...)):
    """
    Perform OCR on an uploaded medical report (PDF, JPG, PNG, WEBP).
    Uses Gemini Vision API for extraction.
    Returns extracted text AND parsed medical profile.
    """
    # Validate file type
    allowed_types = {
        "image/jpeg", "image/jpg", "image/png", "image/webp",
        "image/gif", "application/pdf"
    }
    content_type = file.content_type or ""
    filename = file.filename or ""
    
    # Infer type from filename extension if content_type is generic
    if content_type == "application/octet-stream" or not content_type:
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        ext_map = {
            "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp",
            "gif": "image/gif", "pdf": "application/pdf"
        }
        content_type = ext_map.get(ext, "image/jpeg")

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}. Please upload a JPG, PNG, WEBP, or PDF file."
        )

    # Limit file size to 10MB
    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    try:
        from app.tools.medical_ocr import perform_medical_ocr
        ocr_result = await perform_medical_ocr(file_bytes)

        # Also parse the extracted text
        from app.services.medical_parser import parse_medical_text
        parsed = parse_medical_text(ocr_result.extracted_text)

        return {
            "extracted_text": ocr_result.extracted_text,
            "confidence_score": ocr_result.confidence_score,
            "parsed_profile": parsed,
            "filename": filename
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

# --- Query Agent Endpoint ---

@app.post("/api/query", tags=["Agents"])
async def run_query(req: QueryRequest):
    """
    Process a natural language query using the QueryAgent.

    Supports intent types:
    - safety_check: "Can I eat sushi in Tokyo?"
    - agmarknet_price: "What is the price of Bajra today?"
    - maps_search: "Where is the nearest hospital in Bangkok?"
    """
    try:
        from app.repositories import IFCTRepository, DrugRepository, CuisineRepository, USDARepository
        from app.services.food_knowledge_service import FoodKnowledgeService
        from app.agents.query_agent import QueryAgent

        knowledge_service = FoodKnowledgeService(
            IFCTRepository(), DrugRepository(), CuisineRepository(), USDARepository()
        )
        agent = QueryAgent(knowledge_service)

        user_profile = {
            "allergies": req.allergies or [],
            "medications": req.medications or []
        }

        response = await agent.process_query(req.query, user_profile)
        return {"response": response, "query": req.query}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Live Prices Endpoint ---

@app.get("/api/prices", tags=["Market Data"])
async def get_live_prices():
    """
    Get live agricultural commodity prices from Agmarknet via Fivetran pipeline.
    Returns top-20 commodity prices for the dashboard.
    """
    try:
        from app.tools.agmarknet_tool import AgmarknetTool
        from app.repositories.agmarknet_repository import AgmarknetRepository

        tool = AgmarknetTool()
        repo = AgmarknetRepository(tool)
        prices = await repo.get_live_prices()

        return {
            "count": len(prices),
            "prices": [p.model_dump() for p in prices[:20]],
            "source": "Agmarknet via Fivetran Pipeline"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Fivetran Pipeline Status ---

@app.get("/api/pipeline", tags=["Infrastructure"])
async def get_pipeline_status():
    """
    Get the Fivetran data pipeline status (connectors + BigQuery destination).
    """
    try:
        from app.tools.fivetran_tool import FivetranTool
        tool = FivetranTool()
        summary = tool.get_pipeline_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Destination Info Endpoint ---

@app.get("/api/destination/{destination}", tags=["Travel"])
async def get_destination_info(destination: str):
    """
    Normalize a destination name and return country/cuisine/language metadata.
    """
    from app.services.destination_normalizer import normalize_destination
    return normalize_destination(destination)

# --- Serve Frontend (production) ---

# Mount frontend static files
_frontend_path = _project_root / "frontend"
if _frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_path)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend_path / "index.html"))
