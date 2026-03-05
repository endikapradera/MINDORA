from pathlib import Path
import tempfile

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from app.schemas.documents import IngestResponse
from app.services.ingest import ingest_document

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
