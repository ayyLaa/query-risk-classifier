import os

from fastapi import APIRouter

from src.llm.schema import QueryResponse, QueryRequest, VerdictEnum
from src.services import services

router = APIRouter()

@router.get("/")
async def root():
    return {
        "name": "Query Risk Classifier API",
        "version": "1.0",
        "endpoints": ["/check"]
    }

@router.get("/health")
async def health():
    return {
        "status": "ok"
    }

@router.post("/check")
async def check_query(request: QueryRequest):
    if os.environ.get("LLM_STUB") == "1":
        return QueryResponse(
            verdict=VerdictEnum.safe,
            reason="Stub mode test: Query is safe.",
            confidence=0.95
        )

    raw_response = services.evaluate_query_risk(request.query)
    return {"raw_model_output": raw_response}