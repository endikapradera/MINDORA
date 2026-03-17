from pydantic import BaseModel, Field
from typing import Literal


class LearnPhraseRequest(BaseModel):
    phrase: str = Field(..., min_length=2)
    intent: Literal["explicar", "resumir", "comparar", "ejemplo", "definir", "pasos", "general"] = "general"
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"] = "auto"


class DictionaryEntry(BaseModel):
    phrase: str
    intent: str
    response_style: str


class DictionaryResponse(BaseModel):
    entries: list[DictionaryEntry]


class FeedbackRequest(BaseModel):
    question: str = Field(..., min_length=2)
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"] = "auto"
    useful: bool
