from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np

from app.services.embeddings import embedding_dimension
from app.storage.config import get_base_dir


def _index_path(branch: str) -> Path:
    base = get_base_dir() / "Ramas" / branch / "Index"
    base.mkdir(parents=True, exist_ok=True)
    return base / "faiss.index"


def load_or_create_index(branch: str) -> faiss.IndexIDMap2:
    index_path = _index_path(branch)
    dim = embedding_dimension()
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        if not isinstance(index, faiss.IndexIDMap2):
            index = faiss.IndexIDMap2(index)
        return index

    base_index = faiss.IndexFlatIP(dim)
    return faiss.IndexIDMap2(base_index)


def save_index(branch: str, index: faiss.IndexIDMap2) -> None:
    index_path = _index_path(branch)
    faiss.write_index(index, str(index_path))


def add_embeddings(branch: str, chunk_ids: list[int], vectors: np.ndarray) -> None:
    if not chunk_ids:
        return
    index = load_or_create_index(branch)
    ids = np.array(chunk_ids, dtype="int64")
    index.add_with_ids(vectors, ids)
    save_index(branch, index)


def search(branch: str, vector: np.ndarray, top_k: int = 5) -> tuple[np.ndarray, np.ndarray]:
    index = load_or_create_index(branch)
    if index.ntotal == 0:
        return np.array([], dtype="int64"), np.array([], dtype="float32")
    scores, ids = index.search(vector, top_k)
    return ids[0], scores[0]
