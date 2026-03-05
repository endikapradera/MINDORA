from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: int
    chunks: int
