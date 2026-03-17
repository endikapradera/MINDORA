from __future__ import annotations

import io
import logging
from pathlib import Path

from docx import Document as DocxDocument
from pptx import Presentation
from pypdf import PdfReader
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# Minimum characters per page to consider it "has text" and skip OCR
_OCR_THRESHOLD = 60
# Minimum image size (px) to attempt OCR / description
_MIN_IMG_PX = 80


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


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _ocr_pil_image(img: Image.Image) -> str:
    """Run Tesseract OCR on a PIL image, return cleaned text."""
    try:
        text = pytesseract.image_to_string(img, lang="spa+eng", config="--psm 6")
        return text.strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("OCR error: %s", exc)
        return ""


def _fitz_page_to_pil(fitz_page) -> Image.Image:  # type: ignore[return]
    """Render a PyMuPDF page to a PIL image at 2× resolution for better OCR."""
    mat = __import__("fitz").Matrix(2.0, 2.0)
    pix = fitz_page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def _describe_image_from_bytes(data: bytes, label: str) -> str:
    """
    Try to extract text from an embedded image via OCR.
    Returns a descriptive block like [IMAGEN: <ocr_text>].
    If OCR yields nothing useful, returns a generic placeholder.
    """
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        w, h = img.size
        if w < _MIN_IMG_PX or h < _MIN_IMG_PX:
            return ""
        ocr_text = _ocr_pil_image(img)
        if len(ocr_text) > 20:
            return f"[IMAGEN {label}: {ocr_text}]"
        # No readable text → mark as visual element (diagram/chart)
        aspect = w / h if h else 1.0
        kind = "diagrama" if 0.5 < aspect < 2.5 else "figura"
        return f"[IMAGEN {label}: {kind} sin texto extraíble, tamaño {w}×{h}px]"
    except Exception as exc:  # pragma: no cover
        logger.debug("Image description failed for %s: %s", label, exc)
        return ""


def _extract_pdf(path: Path) -> str:
    """
    Extract text from a PDF.
    - Pages with enough native text → use pypdf (fast).
    - Pages with little/no text → render with PyMuPDF and OCR with Tesseract.
    - Embedded images → OCR + describe inline as [IMAGEN n].
    """
    reader = PdfReader(str(path))

    # Try to import fitz (PyMuPDF) for OCR fallback; gracefully degrade if missing.
    try:
        import fitz  # type: ignore
        fitz_doc = fitz.open(str(path))
        _fitz_available = True
    except ImportError:  # pragma: no cover
        fitz_doc = None
        _fitz_available = False

    parts: list[str] = []
    img_counter = 0

    for i, page in enumerate(reader.pages, start=1):
        native_text = (page.extract_text() or "").strip()

        # --- Native text path ---
        if len(native_text) >= _OCR_THRESHOLD:
            page_parts = [f"[PAGE {i}]\n{native_text}"]
        else:
            # --- OCR fallback path ---
            ocr_text = ""
            if _fitz_available and fitz_doc is not None:
                try:
                    fitz_page = fitz_doc[i - 1]
                    pil_img = _fitz_page_to_pil(fitz_page)
                    ocr_text = _ocr_pil_image(pil_img)
                    logger.info("PAGE %d: OCR aplicado (%d chars)", i, len(ocr_text))
                except Exception as exc:  # pragma: no cover
                    logger.warning("OCR fallback failed for page %d: %s", i, exc)

            combined = (native_text + "\n" + ocr_text).strip()
            page_parts = [f"[PAGE {i}]\n{combined}"] if combined else []

        # --- Embedded images in page ---
        try:
            for img_obj in page.images:
                img_counter += 1
                raw = img_obj.data
                desc = _describe_image_from_bytes(raw, f"p{i}-{img_counter}")
                if desc:
                    page_parts.append(desc)
        except Exception:  # pragma: no cover
            pass  # pypdf may not expose images on all versions

        parts.extend(page_parts)

    if _fitz_available and fitz_doc is not None:
        fitz_doc.close()

    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text)


def _extract_pptx(path: Path) -> str:
    prs = Presentation(str(path))
    parts: list[str] = []
    for i, slide in enumerate(prs.slides, start=1):
        slide_parts: list[str] = []
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text = shape.text.strip()
                if text:
                    slide_parts.append(text)
        if slide_parts:
            parts.append(f"[SLIDE {i}]\n" + "\n".join(slide_parts))
    return "\n".join(parts)


def _extract_image(path: Path) -> str:
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img, lang="spa+eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Tesseract OCR no está instalado en el sistema. Instálalo para procesar imágenes."
        ) from exc
