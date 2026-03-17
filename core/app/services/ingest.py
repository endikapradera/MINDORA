from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import select

from app.services.chunking import chunk_text_with_metadata
from app.services.embeddings import embed_texts
from app.services.index import add_embeddings
from app.services.text_extract import extract_text_from_file
from app.storage.branches import get_branch_path, branch_exists
from app.storage.database import get_session
from app.storage.models import Document, Chunk


def ingest_document(branch: str, source_path: Path) -> dict:
    if not branch_exists(branch):
        raise FileNotFoundError()

    branch_path = get_branch_path(branch)
    material_dir = branch_path / "Material"
    material_dir.mkdir(parents=True, exist_ok=True)

    target_path = material_dir / source_path.name
    if source_path != target_path:
        target_path.write_bytes(source_path.read_bytes())

    text = extract_text_from_file(target_path)
    structured_chunks = chunk_text_with_metadata(text, subject=branch, source=target_path.name)
    chunks = [item["text"] for item in structured_chunks]

    with get_session(branch) as session:
        existing = session.exec(
            select(Document).where(Document.branch == branch, Document.path == str(target_path))
        ).first()
        if existing:
            return {"document_id": existing.id, "chunks": 0}

        doc = Document(branch=branch, filename=target_path.name, path=str(target_path))
        session.add(doc)
        session.commit()
        session.refresh(doc)
        doc_id = doc.id

        chunk_rows: list[Chunk] = []
        for idx, chunk in enumerate(chunks):
            metadata = structured_chunks[idx]["metadata"] if idx < len(structured_chunks) else {}
            chunk_rows.append(
                Chunk(
                    document_id=doc.id,
                    branch=branch,
                    chunk_index=idx,
                    text=chunk,
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
            )
        session.add_all(chunk_rows)
        session.commit()

        chunk_ids = [c.id for c in chunk_rows if c.id is not None]

    if chunk_ids:
        vectors = embed_texts(chunks)
        add_embeddings(branch, chunk_ids, vectors)

    return {"document_id": int(doc_id or 0), "chunks": len(chunks)}
