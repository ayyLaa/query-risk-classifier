import os

from fastapi import APIRouter

from src.llm.schema import QueryResponse, QueryRequest, VerdictEnum

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

@router.post("/check", response_model=QueryResponse)
async def check_query(request: QueryRequest):
    if os.environ.get("LLM_STUB") == "1":
        return QueryResponse(
            verdict=VerdictEnum.safe,
            reason="Stub mode test: Query is safe.",
            confidence=0.95
        )


    return None