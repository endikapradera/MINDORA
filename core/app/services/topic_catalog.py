from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from sqlmodel import select

from app.storage.branches import branch_exists
from app.storage.database import get_session
from app.storage.models import Chunk, Document

_GENERIC = {"", "general", "tema general", "subtema general"}


def _normalize_topic(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    text = text.strip("-:·• ")
    if not text:
        return ""
    if len(text) > 110:
        text = text[:110].rstrip()
    return text


def _topic_from_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[_-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return _normalize_topic(stem)


def list_branch_topics(branch: str, max_topics: int = 24) -> list[dict]:
    if not branch_exists(branch):
        raise FileNotFoundError()

    topic_counter: Counter[str] = Counter()

    with get_session(branch) as session:
        chunks = session.exec(select(Chunk).where(Chunk.branch == branch)).all()
        docs = session.exec(select(Document).where(Document.branch == branch)).all()

    for chunk in chunks:
        try:
            metadata = json.loads(chunk.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}

        tema = _normalize_topic(str(metadata.get("tema", "")))
        subtema = _normalize_topic(str(metadata.get("subtema", "")))

        if tema.lower() not in _GENERIC:
            topic_counter[tema] += 3
        if subtema.lower() not in _GENERIC and subtema.lower() != tema.lower():
            topic_counter[subtema] += 1

    if not topic_counter:
        for doc in docs:
            label = _topic_from_filename(doc.filename)
            if label and label.lower() not in _GENERIC:
                topic_counter[label] += 1

    topics = [
        {"name": name, "count": count}
        for name, count in sorted(topic_counter.items(), key=lambda item: (-item[1], item[0].lower()))[:max_topics]
    ]
    return topics
