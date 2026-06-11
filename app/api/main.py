import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(override=False)
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
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/api/mission")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/parse")
async def parse_medical_text(req: ParseRequest):
    from app.services.medical_parser import parse_medical_text as parser
    return parser(req.text)

@app.post("/api/ocr")
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
async def run_query(req: QueryRequest):
    try:
        from app.repositories import IFCTRepository, DrugRepository, CuisineRepository, USDARepository
        from app.services.food_knowledge_service import FoodKnowledgeService
        from app.agents.query_agent import QueryAgent
        service = FoodKnowledgeService(IFCTRepository(), DrugRepository(), CuisineRepository(), USDARepository())
        agent = QueryAgent(service)
        
        response = await agent.process_query(
            req.query,
            {"conditions": req.conditions, "allergies": req.allergies, "medications": req.medications},
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/destination/{destination}")
async def get_destination_info(destination: str):
    from app.services.destination_normalizer import normalize_destination
    return normalize_destination(destination)

_frontend = _project_root / "frontend"
if _frontend.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend)), name="static")
    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_frontend / "index.html"))