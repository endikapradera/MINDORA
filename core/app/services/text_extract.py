from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader
from PIL import Image
import pytesseract


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".docx":
        return _extract_docx(path)
    if suffix == ".pptx":
        return _extract_pptx(path)
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        return _extract_image(path)
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError("Unsupported file type")


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _extract_pptx(path: Path) -> str:
    prs = Presentation(str(path))
    parts: list[str] = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text = shape.text.strip()
                if text:
                    parts.append(text)
    return "\n".join(parts)


def _extract_image(path: Path) -> str:
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, lang="spa+eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR no está instalado en el sistema. Instálalo para procesar imágenes."
        ) from exc
