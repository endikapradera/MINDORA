from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.schemas.exams import (
    ExamGenerateRequest,
    ExamGenerateResponse,
    ExamExportResponse,
    ExamSolveUploadResponse,
    ExamSimulationStartRequest,
    ExamSimulationStartResponse,
    ExamSimulationSubmitRequest,
    ExamSimulationSubmitResponse,
    ExamSimulationHistoryResponse,
)
from app.services.exams import (
    generate_exam,
    export_exam_pdf,
    export_exam_docx,
    solve_uploaded_exam,
    start_exam_simulation,
    submit_exam_simulation,
    get_simulation_history,
)

router = APIRouter()


@router.post("/generate", response_model=ExamGenerateResponse)
def generate(payload: ExamGenerateRequest, branch: str):
    try:
        result = generate_exam(
            branch,
            payload.topic,
            payload.num_questions,
            payload.difficulty,
            payload.top_k,
            payload.exam_type,
        )
        return ExamGenerateResponse(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/export/pdf", response_model=ExamExportResponse)
def export_pdf(exam_id: str, branch: str, kind: str = "exam"):
    try:
        if kind not in {"exam", "answer_key"}:
            raise HTTPException(status_code=400, detail="Invalid kind. Use 'exam' or 'answer_key'.")
        path = export_exam_pdf(branch, exam_id, kind=kind)
        return ExamExportResponse(path=str(path))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")


@router.post("/export/docx", response_model=ExamExportResponse)
def export_docx(exam_id: str, branch: str, kind: str = "exam"):
    try:
        if kind not in {"exam", "answer_key"}:
            raise HTTPException(status_code=400, detail="Invalid kind. Use 'exam' or 'answer_key'.")
        path = export_exam_docx(branch, exam_id, kind=kind)
        return ExamExportResponse(path=str(path))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")


@router.post("/solve-upload", response_model=ExamSolveUploadResponse)
def solve_upload(branch: str = Form(...), file: UploadFile = File(...), top_k: int = Form(8)):
    suffix = Path(file.filename).suffix.lower()
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = Path(tmp.name)

        try:
            solved = solve_uploaded_exam(branch, tmp_path, top_k=top_k)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        return ExamSolveUploadResponse(**solved)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/simulation/start", response_model=ExamSimulationStartResponse)
def simulation_start(payload: ExamSimulationStartRequest, branch: str):
    try:
        result = start_exam_simulation(branch, payload.exam_id, payload.duration_minutes)
        return ExamSimulationStartResponse(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch or exam not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/simulation/submit", response_model=ExamSimulationSubmitResponse)
def simulation_submit(payload: ExamSimulationSubmitRequest, branch: str):
    try:
        result = submit_exam_simulation(
            branch,
            payload.simulation_id,
            [a.model_dump() for a in payload.answers],
        )
        return ExamSimulationSubmitResponse(**result)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch, exam or simulation not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/simulation/history", response_model=ExamSimulationHistoryResponse)
def simulation_history(branch: str, limit: int = 30):
    try:
        return ExamSimulationHistoryResponse(**get_simulation_history(branch, limit=limit))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch not found")
