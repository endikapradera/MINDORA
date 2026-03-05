from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.services.query import retrieve_chunks
from app.services.llm import generate_answer
from app.storage.branches import get_branch_path, branch_exists


def _exams_dir(branch: str) -> Path:
    return get_branch_path(branch) / "Exams"


def generate_exam(branch: str, topic: str, num_questions: int, difficulty: str, top_k: int) -> dict:
    if not branch_exists(branch):
        raise FileNotFoundError()

    contexts = retrieve_chunks(branch, topic, top_k)
    context_texts = [c["text"] for c in contexts]

    prompt = (
        f"Genera un examen educativo sobre: {topic}. "
        f"Dificultad: {difficulty}. "
        f"Incluye {num_questions} preguntas con respuesta. "
        "Formato: '1) Pregunta ...\nRespuesta: ...' por cada una."
    )
    content = generate_answer(prompt, context_texts)

    exams_dir = _exams_dir(branch)
    exams_dir.mkdir(parents=True, exist_ok=True)
    exam_id = uuid.uuid4().hex
    filename = f"exam_{exam_id}.json"
    payload = {
        "id": exam_id,
        "topic": topic,
        "difficulty": difficulty,
        "num_questions": num_questions,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
    }
    (exams_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"exam_id": exam_id, "filename": filename, "content": content}


def export_exam_pdf(branch: str, exam_id: str) -> Path:
    exam = _load_exam(branch, exam_id)
    exams_dir = _exams_dir(branch)
    path = exams_dir / f"exam_{exam_id}.pdf"

    c = canvas.Canvas(str(path), pagesize=LETTER)
    width, height = LETTER
    y = height - 72

    lines = [f"Examen: {exam['topic']}", f"Dificultad: {exam['difficulty']}", ""]
    lines += exam["content"].splitlines()

    for line in lines:
        if y < 72:
            c.showPage()
            y = height - 72
        c.drawString(72, y, line[:120])
        y -= 14

    c.save()
    return path


def export_exam_docx(branch: str, exam_id: str) -> Path:
    exam = _load_exam(branch, exam_id)
    exams_dir = _exams_dir(branch)
    path = exams_dir / f"exam_{exam_id}.docx"

    doc = Document()
    doc.add_heading(f"Examen: {exam['topic']}", level=1)
    doc.add_paragraph(f"Dificultad: {exam['difficulty']}")
    doc.add_paragraph("")
    for line in exam["content"].splitlines():
        doc.add_paragraph(line)
    doc.save(str(path))
    return path


def _load_exam(branch: str, exam_id: str) -> dict:
    if not branch_exists(branch):
        raise FileNotFoundError()
    exams_dir = _exams_dir(branch)
    path = exams_dir / f"exam_{exam_id}.json"
    if not path.exists():
        raise FileNotFoundError()
    return json.loads(path.read_text(encoding="utf-8"))
