from pydantic import BaseModel, Field
from typing import Literal, Optional


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=8, ge=1, le=20)
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero", "codigo"] = "auto"
    session_id: Optional[str] = None
    document_id: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    contexts: list[str]
    sources: list[str] = []
    session_id: Optional[str] = None
