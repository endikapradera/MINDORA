from fastapi import APIRouter, HTTPException

from app.schemas.branch import BranchCreate, BranchResponse
from app.storage.branches import list_branches, create_branch

router = APIRouter()


@router.get("", response_model=list[BranchResponse])
def get_branches():
    return list_branches()


@router.post("", response_model=BranchResponse)
def post_branch(payload: BranchCreate):
    try:
        return create_branch(payload)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Branch already exists")
