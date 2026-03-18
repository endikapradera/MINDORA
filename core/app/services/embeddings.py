from __future__ import annotations

import os
import logging
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def _normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    return vecs / norms


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    preferred_model = os.getenv("IA_OFFLINE_EMBEDDINGS_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    fallback_model = "all-MiniLM-L6-v2"
    try:
        return SentenceTransformer(preferred_model)
    except Exception as exc:
        logger.warning(
            "No se pudo cargar el modelo de embeddings '%s': %s. Usando fallback '%s'.",
            preferred_model,
            exc,
            fallback_model,
        )
        return SentenceTransformer(fallback_model)


def embed_texts(texts: list[str]) -> np.ndarray:
    model = get_model()
    vecs = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return _normalize(vecs.astype("float32"))


def embedding_dimension() -> int:
    model = get_model()
    return model.get_sentence_embedding_dimension()
