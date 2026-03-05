from fastapi import APIRouter

from app.schemas.query import QueryRequest, QueryResponse, ChunkResult
from app.services.query import retrieve_chunks

router = APIRouter()


@router.post("", response_model=QueryResponse)
def query(payload: QueryRequest, branch: str):
    results = retrieve_chunks(branch, payload.question, payload.top_k)
    return QueryResponse(results=[ChunkResult(**r) for r in results])
