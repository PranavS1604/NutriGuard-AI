"""
NutriGuard AI — FastAPI Backend
"""
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=False)

_PLACEHOLDERS = {
    "your_gemini_api_key_here", "your_maps_api_key_here",
    "your_fivetran_api_key_here", "your_fivetran_api_secret_here",
    "nutriguard-ai-hackathon", "your_new_sambanova_key_here"
}
for _key in ["GEMINI_API_KEY", "SAMBANOVA_API_KEY", "GOOGLE_MAPS_API_KEY", "FIVETRAN_API_KEY",
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

class MissionRequest(BaseModel):
    user_id: str = Field(default="anonymous")
    destination: str = Field(..., min_length=2)
    medical_text: Optional[str] = Field(None)
    ocr_text: Optional[str] = Field(None)

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2)
    destination: Optional[str] = None
    conditions: Optional[List[str]] = Field(default_factory=list)
    allergies: Optional[List[str]] = Field(default_factory=list)
    medications: Optional[List[str]] = Field(default_factory=list)

class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="NutriGuard AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "NutriGuard AI",
        "version": "2.0.0",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "sambanova_fallback_configured": bool(os.environ.get("SAMBANOVA_API_KEY")),
        "maps_configured": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
        "fivetran_configured": bool(os.environ.get("FIVETRAN_API_KEY")),
    }

@app.post("/api/mission", tags=["Agents"])
async def run_mission(req: MissionRequest):
    try:
        from app.agents.orchestrator import execute_travel_health_mission
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse", tags=["Medical"])
async def parse_medical_text(req: ParseRequest):
    from app.services.medical_parser import parse_medical_text as parser
    return parser(req.text)

@app.post("/api/ocr", tags=["Medical"])
async def ocr_medical_report(file: UploadFile = File(...)):
    file_bytes = await file.read()
    try:
        from app.tools.medical_ocr import perform_medical_ocr
        from app.services.medical_parser import parse_medical_text as parser

        ocr_result = await perform_medical_ocr(file_bytes)
        parsed = parser(ocr_result.extracted_text) if ocr_result.extracted_text else {}

        return {
            "extracted_text": ocr_result.extracted_text,
            "confidence_score": ocr_result.confidence_score,
            "parsed_profile": parsed,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query", tags=["Agents"])
async def run_query(req: QueryRequest):
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
            {
                "conditions": req.conditions or [], 
                "allergies": req.allergies or [], 
                "medications": req.medications or []
            },
        )
        return {"response": response, "query": req.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prices", tags=["Market Data"])
async def get_live_prices():
    try:
        from app.tools.agmarknet_tool import AgmarknetTool
        from app.repositories.agmarknet_repository import AgmarknetRepository

        repo = AgmarknetRepository(AgmarknetTool())
        prices = await repo.get_live_prices()
        return {
            "count": len(prices),
            "prices": [p.model_dump() for p in prices[:20]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/destination/{destination}", tags=["Travel"])
async def get_destination_info(destination: str):
    from app.services.destination_normalizer import normalize_destination
    return normalize_destination(destination)

_frontend = _project_root / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend / "index.html"))