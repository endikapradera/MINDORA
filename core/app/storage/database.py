from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from app.storage import models

from app.storage.config import get_base_dir


def get_branch_db_path(branch: str) -> Path:
    base = get_base_dir() / "Ramas" / branch
    return base / "db.sqlite"


def get_engine(branch: str):
    db_path = get_branch_db_path(branch)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    return engine


def get_session(branch: str) -> Session:
    engine = get_engine(branch)
    return Session(engine)
