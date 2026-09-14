from pydantic import BaseModel, Field
from enum import Enum

class QueryRequest(BaseModel):
    query: str = Field(..., max_length=2000)

class VerdictEnum(str, Enum):
    safe = "safe"
    suspicious = "suspicious"
    blocked = "blocked"

class QueryResponse(BaseModel):
    verdict: VerdictEnum
    reason: str
    confidence: float