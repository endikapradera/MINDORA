from typing import Literal, Optional

from pydantic import BaseModel, Field


class ExamGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    num_questions: int = Field(default=10, ge=1, le=50)
    difficulty: str = Field(default="media")
    top_k: int = Field(default=6, ge=1, le=20)
    exam_type: Literal["test"] = "test"


class ExamGenerateResponse(BaseModel):
    exam_id: str
    filename: str
    exam_content: str
    answer_key_content: str
    avg_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    distractor_warnings: list[str] = []


class ExamTopicItem(BaseModel):
    name: str
    count: int = Field(default=1, ge=0)


class ExamTopicsResponse(BaseModel):
    branch: str
    topics: list[ExamTopicItem]


class ExamExportResponse(BaseModel):
    path: str


class ExamSolveUploadResponse(BaseModel):
    solutions: str
    avg_solution_confidence: Optional[float] = None


class SimulationQuestion(BaseModel):
    number: int
    type: str
    statement: str
    options: list[str] = []


class ExamSimulationStartRequest(BaseModel):
    exam_id: str = Field(..., min_length=1)
    duration_minutes: int = Field(default=30, ge=5, le=240)


class ExamSimulationStartResponse(BaseModel):
    simulation_id: str
    exam_id: str
    topic: str
    duration_minutes: int
    started_at: str
    expires_at: str
    questions: list[SimulationQuestion]


class SimulationAnswerItem(BaseModel):
    number: int
    answer: str


class ExamSimulationSubmitRequest(BaseModel):
    simulation_id: str = Field(..., min_length=1)
    answers: list[SimulationAnswerItem] = []


class SimulationResultItem(BaseModel):
    number: int
    type: str
    statement: str
    student_answer: str
    expected_answer: str
    correct: bool
    feedback: str
    question_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExamSimulationSubmitResponse(BaseModel):
    simulation_id: str
    exam_id: str
    topic: str
    total_questions: int
    answered_questions: int
    correct_answers: int
    score_percent: float
    status: str
    weak_topics: list[str]
    results: list[SimulationResultItem]
    avg_question_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExamSimulationHistoryItem(BaseModel):
    simulation_id: str
    exam_id: str
    topic: str
    started_at: str
    submitted_at: Optional[str] = None
    status: str
    score_percent: Optional[float] = None


class ExamSimulationHistoryResponse(BaseModel):
    items: list[ExamSimulationHistoryItem]
