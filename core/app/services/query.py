from __future__ import annotations

import re
from typing import Optional

from sqlmodel import select

from app.services.embeddings import embed_texts
from app.services.index import search
from app.storage.database import get_session
from app.storage.models import Chunk, Document


def _normalize_for_dedup(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúñ0-9]{4,}", (text or "").lower()))


def retrieve_chunks(branch: str, question: str, top_k: int = 5, document_id: Optional[int] = None) -> list[dict]:
    vector = embed_texts([question])
    ids, scores = search(branch, vector, top_k=max(top_k * 8, 20 if document_id else 10))
    if ids.size == 0:
        return []

    id_list = [int(i) for i in ids if i != -1]
    if not id_list:
        return []

    with get_session(branch) as session:
        chunks = session.exec(select(Chunk).where(Chunk.id.in_(id_list))).all()
        documents = session.exec(
            select(Document).where(Document.id.in_([c.document_id for c in chunks]))
        ).all()

    chunk_map = {c.id: c for c in chunks}
    doc_map = {d.id: d for d in documents}
    results: list[dict] = []
    seen: set[str] = set()
    q_tokens = _tokens(question)
    for idx, score in zip(ids.tolist(), scores.tolist()):
        if idx == -1:
            continue
        if float(score) < 0.12:
            continue
        chunk = chunk_map.get(int(idx))
        if not chunk:
            continue
        if document_id is not None and chunk.document_id != document_id:
            continue
        signature = _normalize_for_dedup(chunk.text)
        if signature in seen:
            continue
        seen.add(signature)
        text_tokens = _tokens(chunk.text)
        overlap = len(q_tokens.intersection(text_tokens))
        boosted_score = float(score) + (0.06 * overlap)
        results.append(
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "score": boosted_score,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "filename": (doc_map.get(chunk.document_id).filename if doc_map.get(chunk.document_id) else ""),
                "path": (doc_map.get(chunk.document_id).path if doc_map.get(chunk.document_id) else ""),
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
