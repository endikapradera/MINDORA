from __future__ import annotations

import json
import re
import unicodedata
from collections import OrderedDict
from time import monotonic
from typing import Optional

from sqlmodel import select

from app.services.embeddings import embed_texts
from app.services.index import search
from app.storage.database import get_session
from app.storage.models import Chunk, Document


_CACHE_MAX_ITEMS = 128
_CACHE_TTL_SECONDS = 30.0
_query_cache: "OrderedDict[tuple, tuple[float, list[dict]]]" = OrderedDict()


def _normalize_for_dedup(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def _normalize_text(text: str) -> str:
    lowered = _strip_accents((text or "").lower())
    lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", _normalize_text(text)))


def _ordered_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", _normalize_text(text))


def _parse_metadata(raw: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _intent_hints(question: str) -> dict:
    q = _normalize_text(question)
    return {
        "wants_definition": any(k in q for k in ["que es", "definicion", "define"]),
        "wants_examples": any(k in q for k in ["ejemplo", "ejemplos", "caso practico"]),
        "wants_law": any(k in q for k in ["ley", "articulo", "normativa", "decreto"]),
        "wants_table": any(k in q for k in ["tabla", "comparativa", "comparar"]),
        "wants_steps": any(k in q for k in ["paso a paso", "pasos", "procedimiento"]),
    }


def _phrase_overlap_score(question: str, text: str) -> float:
    q_tokens = _ordered_tokens(question)
    t_tokens = _ordered_tokens(text)
    if not q_tokens or not t_tokens:
        return 0.0

    q_bigrams = {f"{q_tokens[i]} {q_tokens[i+1]}" for i in range(len(q_tokens) - 1)}
    t_bigrams = {f"{t_tokens[i]} {t_tokens[i+1]}" for i in range(len(t_tokens) - 1)}
    if not q_bigrams or not t_bigrams:
        return 0.0
    overlap = len(q_bigrams.intersection(t_bigrams))
    return min(overlap / max(1, len(q_bigrams)), 1.0)


def _intent_metadata_bonus(intent: dict, metadata: dict) -> float:
    if not isinstance(metadata, dict):
        return 0.0
    content_type = str(metadata.get("tipo_contenido", "")).lower()
    bonus = 0.0
    if intent["wants_definition"] and content_type == "definicion":
        bonus += 0.10
    if intent["wants_examples"] and content_type == "ejemplo":
        bonus += 0.10
    if intent["wants_law"] and content_type == "ley_articulo":
        bonus += 0.12
    if intent["wants_table"] and content_type == "tabla":
        bonus += 0.08
    return bonus


def _score_with_metadata(question: str, text: str, base_score: float, metadata: dict) -> float:
    q = (question or "").lower()
    q_tokens = _tokens(question)
    t_tokens = _tokens(text)
    overlap = len(q_tokens.intersection(t_tokens))
    lexical_score = min(overlap / max(len(q_tokens), 1), 1.0)
    phrase_score = _phrase_overlap_score(question, text)
    intent_bonus = _intent_metadata_bonus(_intent_hints(question), metadata)

    boosted = (0.62 * float(base_score)) + (0.24 * lexical_score) + (0.10 * phrase_score) + intent_bonus

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


def _rerank_scored_candidates(candidates: list[dict], top_k: int) -> list[dict]:
    """
    Diversity-aware reranker:
    - Prioritizes high score
    - Penalizes over-representation of same document/theme
    """
    ranked = sorted(candidates, key=lambda x: float(x.get("score", 0.0)), reverse=True)
    if len(ranked) <= top_k:
        return ranked

    selected: list[dict] = []
    doc_counts: dict[int, int] = {}
    theme_counts: dict[str, int] = {}

    while ranked and len(selected) < top_k:
        best_idx = 0
        best_value = -10.0
        for i, item in enumerate(ranked):
            doc_id = int(item.get("document_id", -1))
            theme = str(item.get("tema", "")).strip().lower()
            base = float(item.get("score", 0.0))

            doc_penalty = 0.07 * doc_counts.get(doc_id, 0)
            theme_penalty = 0.05 * theme_counts.get(theme, 0)
            value = base - doc_penalty - theme_penalty

            if value > best_value:
                best_value = value
                best_idx = i

        chosen = ranked.pop(best_idx)
        selected.append(chosen)
        doc_id = int(chosen.get("document_id", -1))
        theme = str(chosen.get("tema", "")).strip().lower()
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        theme_counts[theme] = theme_counts.get(theme, 0) + 1

    return selected


def _effective_score_threshold(question: str) -> float:
    q_tokens = _tokens(question)
    if len(q_tokens) <= 2:
        return 0.04
    if len(q_tokens) <= 4:
        return 0.06
    return 0.08


def retrieve_chunks(branch: str, question: str, top_k: int = 5, document_id: Optional[int] = None) -> list[dict]:
    cache_key = (branch, question.strip().lower(), int(top_k), int(document_id or 0))
    now = monotonic()
    cached = _query_cache.get(cache_key)
    if cached and (now - cached[0]) <= _CACHE_TTL_SECONDS:
        _query_cache.move_to_end(cache_key)
        return [dict(x) for x in cached[1]]

    vector = embed_texts([question])
    candidate_k = max(20, top_k * 4)
    min_score = _effective_score_threshold(question)
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
        if float(score) < min_score:
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
    reranked = _rerank_scored_candidates(results, top_k=top_k)
    final = sorted(reranked, key=lambda x: x["score"], reverse=True)

    _query_cache[cache_key] = (now, [dict(x) for x in final])
    _query_cache.move_to_end(cache_key)
    while len(_query_cache) > _CACHE_MAX_ITEMS:
        _query_cache.popitem(last=False)

    return final
