from pathlib import Path

from app.schemas.branch import BranchCreate, BranchResponse
from app.storage.config import get_base_dir


def _branches_root() -> Path:
    base_dir = get_base_dir()
    return base_dir / "Ramas"


def get_branch_path(branch: str) -> Path:
    return _branches_root() / branch


def branch_exists(branch: str) -> bool:
    return get_branch_path(branch).exists()


def list_branches() -> list[BranchResponse]:
    root = _branches_root()
    if not root.exists():
        return []
    branches: list[BranchResponse] = []
    for item in sorted(root.iterdir()):
        if item.is_dir():
            branches.append(BranchResponse(name=item.name, path=str(item)))
    return branches


def create_branch(payload: BranchCreate) -> BranchResponse:
    root = _branches_root()
    root.mkdir(parents=True, exist_ok=True)
    branch_path = root / payload.name
    if branch_path.exists():
        raise FileExistsError()

    (branch_path / "Material").mkdir(parents=True)
    (branch_path / "Index").mkdir(parents=True)
    (branch_path / "Chats").mkdir(parents=True)
    (branch_path / "Exams").mkdir(parents=True)

    settings_path = branch_path / "settings.json"
    settings_path.write_text("{}", encoding="utf-8")

    return BranchResponse(name=payload.name, path=str(branch_path))
