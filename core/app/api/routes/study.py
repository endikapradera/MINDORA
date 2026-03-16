from fastapi import APIRouter, HTTPException

from app.schemas.study import StudyPackRequest, StudyPackResponse, DailyRecommendationsResponse
from app.services.study import generate_study_pack, get_daily_recommendations

router = APIRouter()


@router.post("/topic-pack", response_model=StudyPackResponse)
def topic_pack(payload: StudyPackRequest, branch: str):
    try:
        return StudyPackResponse(**generate_study_pack(branch, payload.topic, payload.top_k))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/daily-recommendations", response_model=DailyRecommendationsResponse)
def daily_recommendations(branch: str, max_items: int = 5):
    try:
        result = get_daily_recommendations(branch, max_recommendations=max_items)
        return DailyRecommendationsResponse(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Rama no encontrada.")
