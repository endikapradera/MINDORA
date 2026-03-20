from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.storage.branches import get_branch_path, branch_exists


def _chat_file(branch: str, session_id: str) -> Path:
    return get_branch_path(branch) / "Chats" / f"{session_id}.json"


def _chats_dir(branch: str) -> Path:
    return get_branch_path(branch) / "Chats"


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_chat_history(branch: str, session_id: str, max_turns: int = 6) -> list[dict]:
    if not session_id or not branch_exists(branch):
        return []
    path = _chat_file(branch, session_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages", [])
    if len(messages) <= max_turns * 2:
        return messages
    return messages[-(max_turns * 2) :]


def get_full_history(branch: str, session_id: str) -> list[dict]:
    """Return ALL messages for a session (used to reload a past conversation)."""
    if not session_id or not branch_exists(branch):
        return []
    path = _chat_file(branch, session_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("messages", [])


def session_exists(branch: str, session_id: str) -> bool:
    return _chat_file(branch, session_id).exists()


# ── Write helpers ─────────────────────────────────────────────────────────────

def append_chat_turn(branch: str, session_id: str, question: str, answer: str) -> None:
    if not session_id or not branch_exists(branch):
        return
    path = _chat_file(branch, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"messages": [], "created_at": datetime.now(timezone.utc).isoformat()}

    data["messages"].append({"role": "user", "content": question})
    data["messages"].append({"role": "assistant", "content": answer})
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def rename_session(branch: str, session_id: str, new_title: str) -> bool:
    """Persist a custom title for a session. Returns True if it existed."""
    path = _chat_file(branch, session_id)
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    data["title"] = new_title.strip()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def set_session_pinned(branch: str, session_id: str, pinned: bool) -> bool:
    path = _chat_file(branch, session_id)
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    data["pinned"] = bool(pinned)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


# ── Session management ────────────────────────────────────────────────────────

def _session_title(data: dict) -> str:
    """Derive display title: stored title → first user message → fallback."""
    if data.get("title"):
        return data["title"]
    for msg in data.get("messages", []):
        if msg.get("role") == "user":
            raw = msg.get("content", "")
            # Truncate to 60 chars, strip newlines
            short = re.sub(r"\s+", " ", raw).strip()[:60]
            return short + ("…" if len(raw.strip()) > 60 else "")
    return "Conversación sin título"


def list_sessions(branch: str, q: Optional[str] = None) -> list[dict]:
    """Return metadata for all sessions in a branch, newest first."""
    if not branch_exists(branch):
        return []
    chats_dir = _chats_dir(branch)
    if not chats_dir.exists():
        return []
    sessions = []
    for json_file in chats_dir.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        session_id = json_file.stem
        msgs = data.get("messages", [])
        title = _session_title(data)
        session_item = {
            "session_id": session_id,
            "title": title,
            "message_count": len(msgs),
            "pinned": bool(data.get("pinned", False)),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get(
                "updated_at",
                # Fall back to file mtime formatted as ISO string
                datetime.fromtimestamp(json_file.stat().st_mtime, tz=timezone.utc).isoformat()
            ),
        }
        if q and q.strip():
            needle = q.strip().lower()
            haystack = f"{title} {session_id}".lower()
            if needle not in haystack:
                continue
        sessions.append(session_item)

    sessions.sort(key=lambda s: (bool(s.get("pinned", False)), s.get("updated_at", "")), reverse=True)
    return sessions


def delete_session(branch: str, session_id: str) -> bool:
    """Delete a session file. Returns True if it existed."""
    path = _chat_file(branch, session_id)
    if not path.exists():
        return False
    path.unlink()
    return True
