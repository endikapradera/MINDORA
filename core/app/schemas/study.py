from pydantic import BaseModel, Field


class StudyPackRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)


class StudyPackResponse(BaseModel):
    topic: str
    summary_short: str
    summary_long: str
    key_ideas: list[str]
    concepts_to_memorize: list[str]
    possible_exam_questions: list[str]
    common_mistakes: list[str]
    mini_test: list[str]
    sources: list[str]


class DailyRecommendationItem(BaseModel):
    topic: str
    fail_count: int
    last_failed: str
    suggestion: str


class DailyRecommendationsResponse(BaseModel):
    recommendations: list[DailyRecommendationItem]
    message: str
