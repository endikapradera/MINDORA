from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sqlmodel import select

from app.schemas.documents import IngestResponse
from app.schemas.documents_list import DocumentListResponse, DocumentItem
from app.services.ingest import ingest_document
from app.storage.database import get_session
from app.storage.models import Document

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest(branch: str = Form(...), file: UploadFile = File(...)):
    try:
        suffix = Path(file.filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file.file.read())
            tmp_path = Path(tmp.name)
        try:
            result = ingest_document(branch, tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return IngestResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch not found")


@router.get("", response_model=DocumentListResponse)
def list_documents(branch: str):
    with get_session(branch) as session:
        rows = session.exec(select(Document).where(Document.branch == branch)).all()
    return DocumentListResponse(
        documents=[
            DocumentItem(id=row.id, filename=row.filename, path=row.path, created_at=row.created_at)
            for row in rows
            if row.id is not None
        ]
    )
