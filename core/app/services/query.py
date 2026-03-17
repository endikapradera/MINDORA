from __future__ import annotations

import json
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


def _parse_metadata(raw: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _score_with_metadata(question: str, text: str, base_score: float, metadata: dict) -> float:
    q = (question or "").lower()
    q_tokens = _tokens(question)
    t_tokens = _tokens(text)
    overlap = len(q_tokens.intersection(t_tokens))
    lexical_score = min(overlap / max(len(q_tokens), 1), 1.0)

    boosted = (0.72 * float(base_score)) + (0.28 * lexical_score)

    content_type = str(metadata.get("tipo_contenido", "")).lower()
    if any(k in q for k in ["defin", "qué es", "que es"]) and content_type == "definicion":
        boosted += 0.08
    if "ejemplo" in q and content_type == "ejemplo":
        boosted += 0.08
    if any(k in q for k in ["ley", "artículo", "articulo"]) and content_type == "ley_articulo":
        boosted += 0.10
    if any(k in q for k in ["tabla", "comparativa"]) and content_type == "tabla":
        boosted += 0.07

    tema = str(metadata.get("tema", "")).lower()
    subtema = str(metadata.get("subtema", "")).lower()
    if tema and any(tok in tema for tok in q_tokens):
        boosted += 0.03
    if subtema and any(tok in subtema for tok in q_tokens):
        boosted += 0.03

    return boosted


def retrieve_chunks(branch: str, question: str, top_k: int = 5, document_id: Optional[int] = None) -> list[dict]:
    vector = embed_texts([question])
    candidate_k = max(20, top_k * 4)
    ids, scores = search(branch, vector, top_k=candidate_k)
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
    for idx, score in zip(ids.tolist(), scores.tolist()):
        if idx == -1:
            continue
        if float(score) < 0.08:
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
        metadata = _parse_metadata(chunk.metadata_json)
        boosted_score = _score_with_metadata(question, chunk.text, float(score), metadata)
        page = metadata.get("pagina")
        if page is None:
            page = 0
        results.append(
            {
                "chunk_id": chunk.id,
                "text": chunk.text,
                "score": boosted_score,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "filename": (doc_map.get(chunk.document_id).filename if doc_map.get(chunk.document_id) else ""),
                "path": (doc_map.get(chunk.document_id).path if doc_map.get(chunk.document_id) else ""),
                "asignatura": metadata.get("asignatura", branch),
                "tema": metadata.get("tema", "Tema general"),
                "subtema": metadata.get("subtema", "General"),
                "tipo_contenido": metadata.get("tipo_contenido", "teoria"),
                "pagina": page,
                "dificultad": metadata.get("dificultad", "media"),
                "fuente": metadata.get("fuente", (doc_map.get(chunk.document_id).filename if doc_map.get(chunk.document_id) else "")),
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
