from pydantic import BaseModel, Field
from typing import Optional


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=8, ge=1, le=20)
    document_id: Optional[int] = None


class ChunkResult(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    score: float
    text: str
    filename: str = ""
    path: str = ""
    asignatura: str = ""
    tema: str = ""
    subtema: str = ""
    tipo_contenido: str = "teoria"
    pagina: int = 0
    dificultad: str = "media"
    fuente: str = ""


class QueryResponse(BaseModel):
    results: list[ChunkResult]
