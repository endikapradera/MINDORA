from fastapi import APIRouter, HTTPException

from app.schemas.branch import BranchCreate, BranchResponse
from app.storage.branches import list_branches, create_branch, delete_branch

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


@router.delete("")
def remove_branch(name: str):
    try:
        delete_branch(name)
        return {"status": "deleted"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Branch not found")
