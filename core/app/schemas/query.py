from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkResult(BaseModel):
    chunk_id: int
    document_id: int
    score: float
    text: str


class QueryResponse(BaseModel):
    results: list[ChunkResult]
