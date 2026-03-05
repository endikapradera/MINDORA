from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class BranchResponse(BaseModel):
    name: str
    path: str
