from fastapi import APIRouter, HTTPException

from app.schemas.exams import ExamGenerateRequest, ExamGenerateResponse, ExamExportResponse
from app.services.exams import generate_exam, export_exam_pdf, export_exam_docx

router = APIRouter()


@router.post("/generate", response_model=ExamGenerateResponse)
def generate(payload: ExamGenerateRequest, branch: str):
    try:
        result = generate_exam(branch, payload.topic, payload.num_questions, payload.difficulty, payload.top_k)
        return ExamGenerateResponse(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/export/pdf", response_model=ExamExportResponse)
def export_pdf(exam_id: str, branch: str):
    try:
        path = export_exam_pdf(branch, exam_id)
        return ExamExportResponse(path=str(path))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")


@router.post("/export/docx", response_model=ExamExportResponse)
def export_docx(exam_id: str, branch: str):
    try:
        path = export_exam_docx(branch, exam_id)
        return ExamExportResponse(path=str(path))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")
