from datetime import datetime
from pydantic import BaseModel


class DocumentItem(BaseModel):
    id: int
    filename: str
    path: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]
