from __future__ import annotations

import re
from typing import Optional


def _detect_content_type(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return "teoria"
    if "|" in t or "\t" in t or "tabla" in t:
        return "tabla"
    if re.search(r"\b(ley|art[íi]culo|art\.|decreto|normativa)\b", t):
        return "ley_articulo"
    if re.search(r"\b(ejemplo|por ejemplo|caso pr[aá]ctico)\b", t):
        return "ejemplo"
    if re.search(r"\b(definici[oó]n|se define como|es el proceso de|es la)\b", t):
        return "definicion"
    return "teoria"


def _detect_difficulty(text: str) -> str:
    t = (text or "").lower()
    advanced_markers = [
        "teorema",
        "demostraci",
        "algoritmo",
        "complejidad",
        "jurisprudencia",
        "vectoriz",
        "multimodal",
        "cuantiz",
        "inferencia",
    ]
    basic_markers = ["introducci", "b[aá]sico", "concepto", "resumen", "qu[eé] es"]
    if any(m in t for m in advanced_markers):
        return "alta"
    if any(m in t for m in basic_markers):
        return "baja"
    return "media"


def _extract_page(text: str) -> Optional[int]:
    m = re.search(r"\[PAGE\s+(\d+)\]", text)
    if not m:
        return None
    return int(m.group(1))


def _is_heading(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if l.startswith("#"):
        return True
    if re.match(r"^(tema|unidad|cap[ií]tulo|bloque)\s+\d+", l, flags=re.I):
        return True
    if re.match(r"^\d+(\.\d+)*\s+", l):
        return True
    return False


def _normalize_heading(line: str) -> str:
    l = re.sub(r"^#+\s*", "", line.strip())
    l = re.sub(r"\s+", " ", l)
    return l.strip(" -:")


def _split_sections(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n")
    lines = raw.split("\n")
    blocks: list[str] = []
    current: list[str] = []

    for line in lines:
        if _is_heading(line):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            current.append(line.strip())
            continue
        if not line.strip() and current:
            blocks.append("\n".join(current).strip())
            current = []
            continue
        current.append(line)

    if current:
        blocks.append("\n".join(current).strip())

    return [b for b in blocks if b and len(b) >= 20]


def _split_long_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = max(0, end - overlap)
    return chunks


def chunk_text_with_metadata(
    text: str,
    subject: str,
    source: str,
    chunk_size: int = 800,
    overlap: int = 120,
) -> list[dict]:
    sections = _split_sections(text)
    if not sections:
        sections = _split_long_text(text, chunk_size=chunk_size, overlap=overlap)

    current_theme = "Tema general"
    current_subtheme = "General"
    output: list[dict] = []

    for section in sections:
        lines = [x.strip() for x in section.split("\n") if x.strip()]
        if not lines:
            continue

        first_line = lines[0]
        if _is_heading(first_line):
            heading = _normalize_heading(first_line)
            if re.match(r"^(tema|unidad|cap[ií]tulo|bloque)\s+\d+", heading, flags=re.I):
                current_theme = heading
                if len(lines) > 1:
                    current_subtheme = _normalize_heading(lines[1])
            else:
                current_subtheme = heading

        page = _extract_page(section)
        section_type = _detect_content_type(section)
        difficulty = _detect_difficulty(section)

        for text_chunk in _split_long_text(section, chunk_size=chunk_size, overlap=overlap) or [section]:
            output.append(
                {
                    "text": text_chunk,
                    "metadata": {
                        "asignatura": subject,
                        "tema": current_theme,
                        "subtema": current_subtheme,
                        "tipo_contenido": section_type,
                        "pagina": page,
                        "dificultad": difficulty,
                        "fuente": source,
                    },
                }
            )

    return output


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    return _split_long_text(text, chunk_size=chunk_size, overlap=overlap)
