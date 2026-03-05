from fastapi import APIRouter

from app.api.routes.branches import router as branches_router
from app.api.routes.documents import router as documents_router
from app.api.routes.query import router as query_router
from app.api.routes.ask import router as ask_router
from app.api.routes.exams import router as exams_router

api_router = APIRouter()
api_router.include_router(branches_router, prefix="/branches", tags=["branches"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(query_router, prefix="/query", tags=["query"])
api_router.include_router(ask_router, prefix="/ask", tags=["ask"])
api_router.include_router(exams_router, prefix="/exams", tags=["exams"])
