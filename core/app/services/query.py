from __future__ import annotations

from sqlmodel import select

from app.services.embeddings import embed_texts
from app.services.index import search
from app.storage.database import get_session
from app.storage.models import Chunk


def retrieve_chunks(branch: str, question: str, top_k: int = 5) -> list[dict]:
    vector = embed_texts([question])
    ids, scores = search(branch, vector, top_k=top_k)
    if ids.size == 0:
        return []

    id_list = [int(i) for i in ids if i != -1]
    if not id_list:
        return []

    with get_session(branch) as session:
        chunks = session.exec(select(Chunk).where(Chunk.id.in_(id_list))).all()

    chunk_map = {c.id: c for c in chunks}
    results: list[dict] = []
    for idx, score in zip(ids.tolist(), scores.tolist()):
        if idx == -1:
            continue
        chunk = chunk_map.get(int(idx))
        if not chunk:
            continue
        results.append(
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "score": float(score),
                "document_id": chunk.document_id,
            }
        )
    return results
