from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from app.services.topic_catalog import list_branch_topics
from app.storage.database import get_session
from app.storage.models import Chunk, Document


_FAKE_EXAM = """
### Pregunta 1
Tipo: test_simple
Enunciado: ¿Qué es una proposición lógica?
Opciones:
A) Un operador
B) Un enunciado con valor de verdad
C) Una tabla
D) Un conjunto
Respuesta: B
Explicacion: Una proposición lógica es un enunciado que puede ser verdadero o falso.

### Pregunta 2
Tipo: desarrollo
Enunciado: Explica qué es una tabla de verdad.
Opciones:
Respuesta: Representa todas las combinaciones posibles de valores de verdad.
Explicacion: Se usa para analizar proposiciones compuestas.
"""


def _prepare_branch(tmp_path: Path, branch: str) -> Path:
    branch_path = tmp_path / branch
    (branch_path / "Exams").mkdir(parents=True, exist_ok=True)
    return branch_path


def test_list_branch_topics_uses_chunk_metadata(tmp_path: Path):
    branch = "A1 - LOGICA"
    branch_path = _prepare_branch(tmp_path, branch)

    with patch("app.storage.database.get_branch_db_path", return_value=branch_path / "db.sqlite"), patch(
        "app.storage.branches.get_branch_path", return_value=branch_path
    ), patch("app.services.topic_catalog.branch_exists", return_value=True):
        with get_session(branch) as session:
            doc = Document(branch=branch, filename="logica.pdf", path=str(branch_path / "Material" / "logica.pdf"))
            session.add(doc)
            session.commit()
            session.refresh(doc)
            session.add(
                Chunk(
                    document_id=int(doc.id or 1),
                    branch=branch,
                    chunk_index=0,
                    text="texto",
                    metadata_json=json.dumps({"tema": "Proposiciones lógicas", "subtema": "Tablas de verdad"}),
                )
            )
            session.commit()

        topics = list_branch_topics(branch)

    names = [item["name"] for item in topics]
    assert "Proposiciones lógicas" in names
    assert "Tablas de verdad" in names


def test_generate_exam_contains_answer_key(tmp_path: Path):
    branch = "A1 - LOGICA"
    branch_path = _prepare_branch(tmp_path, branch)

    with patch("app.services.exams.get_branch_path", return_value=branch_path), patch(
        "app.services.exams.branch_exists", return_value=True
    ), patch(
        "app.services.exams.retrieve_chunks",
        return_value=[
            {"text": "Las proposiciones lógicas son enunciados con valor de verdad."},
            {"text": "Las tablas de verdad permiten evaluar conectores lógicos."},
        ],
    ), patch("app.services.exams.generate_text", return_value=_FAKE_EXAM):
        from app.services.exams import generate_exam

        result = generate_exam(branch, topic="Proposiciones lógicas", num_questions=2, difficulty="media", top_k=5)

    assert "SOLUCIONARIO - Proposiciones lógicas" in result["answer_key_content"]
    assert "1) Respuesta: B" in result["answer_key_content"]
    assert "2) Respuesta:" in result["answer_key_content"]
