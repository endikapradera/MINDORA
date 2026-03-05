from pydantic import BaseModel, Field


class ExamGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    num_questions: int = Field(default=10, ge=1, le=50)
    difficulty: str = Field(default="media")
    top_k: int = Field(default=6, ge=1, le=20)


class ExamGenerateResponse(BaseModel):
    exam_id: str
    filename: str
    content: str


class ExamExportResponse(BaseModel):
    path: str
