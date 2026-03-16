from __future__ import annotations

import json
from pathlib import Path

from app.storage.branches import get_branch_path, branch_exists


def _chat_file(branch: str, session_id: str) -> Path:
    return get_branch_path(branch) / "Chats" / f"{session_id}.json"


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


def append_chat_turn(branch: str, session_id: str, question: str, answer: str) -> None:
    if not session_id or not branch_exists(branch):
        return
    path = _chat_file(branch, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"messages": []}

    data["messages"].append({"role": "user", "content": question})
    data["messages"].append({"role": "assistant", "content": answer})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
