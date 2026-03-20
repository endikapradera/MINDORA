"""
Routes for managing persisted chat sessions (history panel).

GET    /api/chats/{branch}               → list all sessions
GET    /api/chats/{branch}/{session_id}  → load messages of a session
DELETE /api/chats/{branch}/{session_id}  → delete a session
PATCH  /api/chats/{branch}/{session_id}  → rename a session
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.chat_memory import (
    list_sessions,
    get_full_history,
    delete_session,
    rename_session,
    set_session_pinned,
    session_exists,
)
from app.storage.branches import branch_exists

router = APIRouter()


class RenameRequest(BaseModel):
    title: str


class PinRequest(BaseModel):
    pinned: bool


# ── List all sessions ──────────────────────────────────────────────────────────
@router.get("/{branch}")
def get_sessions(branch: str, q: str | None = Query(default=None)) -> list[dict]:
    """Return session metadata for all saved conversations in a branch."""
    if not branch_exists(branch):
        raise HTTPException(status_code=404, detail=f"Rama '{branch}' no encontrada")
    return list_sessions(branch, q=q)


# ── Load full messages of one session ─────────────────────────────────────────
@router.get("/{branch}/{session_id}")
def load_session(branch: str, session_id: str) -> dict:
    """Return all messages of a specific session."""
    if not branch_exists(branch):
        raise HTTPException(status_code=404, detail=f"Rama '{branch}' no encontrada")
    if not session_exists(branch, session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    messages = get_full_history(branch, session_id)
    return {"session_id": session_id, "messages": messages}


# ── Delete a session ──────────────────────────────────────────────────────────
@router.delete("/{branch}/{session_id}")
def remove_session(branch: str, session_id: str) -> dict:
    """Delete a saved chat session."""
    if not branch_exists(branch):
        raise HTTPException(status_code=404, detail=f"Rama '{branch}' no encontrada")
    deleted = delete_session(branch, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "deleted", "session_id": session_id}


# ── Rename a session ──────────────────────────────────────────────────────────
@router.patch("/{branch}/{session_id}")
def update_session_title(branch: str, session_id: str, body: RenameRequest) -> dict:
    """Rename a chat session (set a custom display title)."""
    if not branch_exists(branch):
        raise HTTPException(status_code=404, detail=f"Rama '{branch}' no encontrada")
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="El título no puede estar vacío")
    updated = rename_session(branch, session_id, body.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "updated", "session_id": session_id, "title": body.title.strip()}


@router.patch("/{branch}/{session_id}/pin")
def update_session_pin(branch: str, session_id: str, body: PinRequest) -> dict:
    """Pin/unpin a chat session."""
    if not branch_exists(branch):
        raise HTTPException(status_code=404, detail=f"Rama '{branch}' no encontrada")
    updated = set_session_pinned(branch, session_id, body.pinned)
    if not updated:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "updated", "session_id": session_id, "pinned": bool(body.pinned)}
