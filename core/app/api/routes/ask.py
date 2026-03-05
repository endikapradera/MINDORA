from fastapi import APIRouter, HTTPException

from app.schemas.ask import AskRequest, AskResponse
from app.services.query import retrieve_chunks
from app.services.llm import generate_answer

router = APIRouter()


@router.post("", response_model=AskResponse)
def ask(payload: AskRequest, branch: str):
    results = retrieve_chunks(branch, payload.question, payload.top_k)
    contexts = [r["text"] for r in results]
    try:
        answer = generate_answer(payload.question, contexts)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AskResponse(answer=answer, contexts=contexts)
