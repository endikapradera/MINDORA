from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from app.storage.config import get_base_dir

ResponseStyle = Literal[
    "auto",
    "corta",
    "detallada",
    "pasos",
    "detallada_pasos",
    "examen",
    "profesor",
    "companero",
]

LEARNABLE_STYLES: set[str] = {
    "corta",
    "detallada",
    "pasos",
    "detallada_pasos",
    "examen",
    "profesor",
    "companero",
}


def _feedback_path() -> Path:
    return get_base_dir() / "style_feedback.json"


def _normalize_phrase(text: str, max_words: int = 7) -> str:
    words = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", (text or "").lower())
    if not words:
        return ""
    return " ".join(words[:max_words]).strip()


def _empty_store() -> dict:
    return {"global": {}, "by_phrase": {}}


def _load_store() -> dict:
    path = _feedback_path()
    if not path.exists():
        return _empty_store()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _empty_store()
        data.setdefault("global", {})
        data.setdefault("by_phrase", {})
        return data
    except Exception:
        return _empty_store()


def _save_store(data: dict) -> None:
    path = _feedback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _style_delta(useful: bool) -> int:
    return 1 if useful else -1


def _bump(bucket: dict, style: str, useful: bool) -> None:
    node = bucket.get(style, {"up": 0, "down": 0, "score": 0})
    if useful:
        node["up"] = int(node.get("up", 0)) + 1
    else:
        node["down"] = int(node.get("down", 0)) + 1
    node["score"] = int(node.get("score", 0)) + _style_delta(useful)
    bucket[style] = node


def record_feedback(question: str, style: ResponseStyle, useful: bool) -> None:
    if style not in LEARNABLE_STYLES:
        return

    store = _load_store()
    _bump(store["global"], style, useful)

    phrase = _normalize_phrase(question)
    if phrase:
        phrase_bucket = store["by_phrase"].get(phrase, {})
        _bump(phrase_bucket, style, useful)
        store["by_phrase"][phrase] = phrase_bucket

    _save_store(store)


def _best_style(bucket: dict) -> str | None:
    if not bucket:
        return None

    ordered = sorted(
        bucket.items(),
        key=lambda kv: (int(kv[1].get("score", 0)), int(kv[1].get("up", 0))),
        reverse=True,
    )
    style, stats = ordered[0]
    if int(stats.get("score", 0)) <= 0:
        return None
    return style


def recommend_style(question: str) -> str | None:
    store = _load_store()

    phrase = _normalize_phrase(question)
    if phrase:
        local_best = _best_style(store.get("by_phrase", {}).get(phrase, {}))
        if local_best:
            return local_best

    return _best_style(store.get("global", {}))
