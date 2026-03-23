from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlmodel import select

os.environ.setdefault("MINDORA_OCR_EMBEDDED_IMAGES", "0")
os.environ.setdefault("MINDORA_OCR_TIMEOUT_SECONDS", "6")

from app.schemas.branch import BranchCreate
from app.services.ingest import ingest_document
from app.storage.branches import branch_exists, create_branch, delete_branch
from app.storage.database import get_session
from app.storage.models import Chunk, Document

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMARIO_ROOT = Path("/Users/endikapraderatouzani/Desktop/MINDORA/TEMARIO ")
SUPPORTED = {".pdf", ".docx", ".pptx", ".txt", ".md"}
TARGET_BRANCHES = [
    "A1 - LOGICA",
    "A2 - DIMENSIONES SEGURIDAD",
    "A3 - ESTADISTICA Y OP",
    "A4 - PRIN. JURIDICOS CIBER",
    "A5 - PROG. ESTRUCTURAS LINEALES",
    "A12 - PROG. CONCURRENTE",
    "A13 - INTELIGENCIA ARTIFICIAL",
    "A14 - MET. DESARROLLO SEGURO",
    "A15 - MET. GESTION PROYECTOS",
]


def iter_branch_files(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED
    )


def count_branch_docs_chunks(branch: str) -> tuple[int, int]:
    with get_session(branch) as session:
        docs = session.exec(select(Document).where(Document.branch == branch)).all()
        chunks = session.exec(select(Chunk).where(Chunk.branch == branch)).all()
    return len(docs), len(chunks)


def refresh_branch(branch: str) -> None:
    if branch_exists(branch):
        delete_branch(branch)
    create_branch(BranchCreate(name=branch))


def ingest_branch(branch: str, folder: Path) -> dict[str, Any]:
    files = iter_branch_files(folder)
    print(f"\n=== {branch} ===", flush=True)
    print(f"Documentos detectados: {len(files)}", flush=True)
    refresh_branch(branch)
    print("Rama creada", flush=True)

    docs_ok = 0
    chunks = 0
    errors: list[dict[str, str]] = []

    for idx, path in enumerate(files, start=1):
        rel = path.relative_to(folder)
        try:
            result = ingest_document(branch, path)
            chunk_count = int(result.get("chunks", 0))
            docs_ok += 1
            chunks += chunk_count
            print(f"[{idx}/{len(files)}] OK  {rel} -> chunks={chunk_count}", flush=True)
        except BaseException as exc:
            errors.append({"file": str(rel), "error": str(exc)})
            print(f"[{idx}/{len(files)}] ERR {rel} -> {exc}", flush=True)

    docs_db, chunks_db = count_branch_docs_chunks(branch)
    print(
        f"RESUMEN {branch}: docs_ok={docs_ok}/{len(files)} chunks={chunks} errores={len(errors)}",
        flush=True,
    )
    return {
        "docs_detected": len(files),
        "docs_ok": docs_ok,
        "chunks_ingested": chunks,
        "errors": errors,
        "docs_db": docs_db,
        "chunks_db": chunks_db,
    }


def ingest_principal() -> dict[str, Any]:
    branch = "principal"
    root_questions = TEMARIO_ROOT / "preguntas-temario.txt"
    if not root_questions.exists():
        return {
            "docs_detected": 0,
            "docs_ok": 0,
            "chunks_ingested": 0,
            "errors": [{"file": "preguntas-temario.txt", "error": "missing file"}],
            "docs_db": 0,
            "chunks_db": 0,
        }

    print("\n=== principal ===", flush=True)
    refresh_branch(branch)
    result = ingest_document(branch, root_questions)
    chunk_count = int(result.get("chunks", 0))
    docs_db, chunks_db = count_branch_docs_chunks(branch)
    print(f"Banco principal cargado -> chunks={chunk_count}", flush=True)
    return {
        "docs_detected": 1,
        "docs_ok": 1,
        "chunks_ingested": chunk_count,
        "errors": [],
        "docs_db": docs_db,
        "chunks_db": chunks_db,
    }


def main() -> int:
    os.environ.setdefault("IA_OFFLINE_BASE_DIR", str((PROJECT_ROOT / "data").resolve()))
    summaries: dict[str, dict[str, Any]] = {}

    for branch in TARGET_BRANCHES:
        folder = TEMARIO_ROOT / branch
        if not folder.exists():
            summaries[branch] = {
                "docs_detected": 0,
                "docs_ok": 0,
                "chunks_ingested": 0,
                "errors": [{"file": ".", "error": "source folder missing"}],
                "docs_db": 0,
                "chunks_db": 0,
            }
            continue
        summaries[branch] = ingest_branch(branch, folder)

    summaries["principal"] = ingest_principal()

    print("\n=== RESUMEN POR RAMA ===", flush=True)
    total_docs = 0
    total_chunks = 0
    total_errors = 0
    for branch in TARGET_BRANCHES + ["principal"]:
        info = summaries[branch]
        total_docs += info["docs_ok"]
        total_chunks += info["chunks_ingested"]
        total_errors += len(info["errors"])
        print(
            f"{branch} | docs_ok={info['docs_ok']}/{info['docs_detected']} | "
            f"chunks_ingest={info['chunks_ingested']} | docs_db={info['docs_db']} | "
            f"chunks_db={info['chunks_db']} | errors={len(info['errors'])}",
            flush=True,
        )

    print("\n=== RESUMEN GLOBAL ===", flush=True)
    print(f"Documentos cargados: {total_docs}", flush=True)
    print(f"Chunks generados: {total_chunks}", flush=True)
    print(f"Errores totales: {total_errors}", flush=True)
    if total_errors:
        print("\n=== ERRORES ===", flush=True)
        for branch in TARGET_BRANCHES + ["principal"]:
            for item in summaries[branch]["errors"]:
                print(f"- [{branch}] {item['file']}: {item['error']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
