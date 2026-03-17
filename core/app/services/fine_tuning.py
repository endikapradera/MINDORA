from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.storage.config import get_base_dir
from app.storage.branches import list_branches, get_branch_path


READY_MIN_EXAMPLES = 120


def _ft_dir() -> Path:
    path = get_base_dir() / "fine_tuning"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _approved_examples_path() -> Path:
    return _ft_dir() / "approved_examples.jsonl"


def _dataset_path() -> Path:
    return _ft_dir() / "lora_dataset.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue
    return rows


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def record_approved_example(
    question: str,
    answer: str,
    style: str,
    branch: str | None = None,
) -> None:
    question = (question or "").strip()
    answer = (answer or "").strip()
    style = (style or "auto").strip()
    if not question or not answer or style == "auto":
        return

    prompt = f"[MODO={style}] {question}" if style else question
    row = {
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ],
        "style": style,
        "source": "feedback",
        "branch": branch,
    }
    _append_jsonl(_approved_examples_path(), row)


def _extract_examples_from_chats(max_per_branch: int = 30) -> list[dict]:
    examples: list[dict] = []
    for b in list_branches():
        branch_name = b.name
        chats_dir = get_branch_path(branch_name) / "Chats"
        if not chats_dir.exists():
            continue
        collected = 0
        for chat_file in sorted(chats_dir.glob("*.json"), reverse=True):
            if collected >= max_per_branch:
                break
            try:
                data = json.loads(chat_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            msgs = data.get("messages", [])
            for i in range(len(msgs) - 1):
                u = msgs[i]
                a = msgs[i + 1]
                if u.get("role") == "user" and a.get("role") == "assistant":
                    uq = str(u.get("content", "")).strip()
                    aa = str(a.get("content", "")).strip()
                    if uq and aa:
                        examples.append(
                            {
                                "messages": [
                                    {"role": "user", "content": uq},
                                    {"role": "assistant", "content": aa},
                                ],
                                "style": "unknown",
                                "source": "chat",
                                "branch": branch_name,
                            }
                        )
                        collected += 1
                        if collected >= max_per_branch:
                            break
    return examples


def export_lora_dataset(include_chats: bool = True) -> dict:
    approved = _read_jsonl(_approved_examples_path())
    merged = list(approved)
    if include_chats:
        merged.extend(_extract_examples_from_chats())

    # de-duplicate by user+assistant pair
    seen: set[str] = set()
    unique_rows: list[dict] = []
    for row in merged:
        msgs = row.get("messages", [])
        if len(msgs) < 2:
            continue
        key = (msgs[0].get("content", "") + "||" + msgs[1].get("content", "")).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    out_path = _dataset_path()
    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in unique_rows) + ("\n" if unique_rows else ""),
        encoding="utf-8",
    )

    style_counter = Counter(str(r.get("style", "unknown")) for r in unique_rows)
    ready = len(unique_rows) >= READY_MIN_EXAMPLES

    return {
        "path": str(out_path),
        "examples": len(unique_rows),
        "ready": ready,
        "min_required": READY_MIN_EXAMPLES,
        "style_distribution": dict(style_counter),
    }


def get_fine_tune_status() -> dict:
    approved = _read_jsonl(_approved_examples_path())
    style_counter = Counter(str(r.get("style", "unknown")) for r in approved)
    total = len(approved)
    return {
        "approved_examples": total,
        "ready": total >= READY_MIN_EXAMPLES,
        "min_required": READY_MIN_EXAMPLES,
        "style_distribution": dict(style_counter),
        "dataset_path": str(_dataset_path()),
    }
