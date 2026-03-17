from pydantic import BaseModel, Field
from typing import Literal, Optional


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
    answer_text: Optional[str] = None
    branch: Optional[str] = None


class FineTuneStatusResponse(BaseModel):
    approved_examples: int
    ready: bool
    min_required: int
    style_distribution: dict[str, int]
    dataset_path: str


class FineTuneExportResponse(BaseModel):
    path: str
    examples: int
    ready: bool
    min_required: int
    style_distribution: dict[str, int]
