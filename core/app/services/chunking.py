from __future__ import annotations

import re
from typing import Optional


def _detect_content_type(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return "teoria"
    if "|" in t or "\t" in t or "tabla" in t:
        return "tabla"
    has_legal_marker = bool(
        re.search(r"\b(ley|decreto|normativa)\b", t)
        or re.search(r"\bart[íi]?culo\s+\d+\b", t)
        or re.search(r"\bart\.\s*\d+\b", t)
    )
    if has_legal_marker:
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
    matches = re.findall(r"\[PAGE\s+(\d+)\]", text)
    if not matches:
        return None
    return int(matches[-1])


def _is_page_marker(line: str) -> bool:
    return bool(re.match(r"^\[PAGE\s+\d+\]$", line.strip(), flags=re.I))


def _is_heading(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if _is_page_marker(l):
        return True
    if l.startswith("#"):
        return True
    if re.match(r"^(tema|unidad|cap[ií]tulo|bloque)\s+\d+", l, flags=re.I):
        return True
    # 1. Título / 1) Título / 1.1 Título
    if re.match(r"^\d+([\.)]|\.\d+)+\s+", l):
        return True
    if re.match(r"^\d+[\.)]\s+", l):
        return True
    # Bullet con aspecto de subtítulo
    if re.match(r"^[●○■\-]\s+[A-ZÁÉÍÓÚÑ][^\n]{4,90}:?$", l):
        return True
    # Línea completamente en mayúsculas (títulos OCR)
    if re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{8,}$", l):
        return True
    return False


def _normalize_heading(line: str) -> str:
    l = re.sub(r"^#+\s*", "", line.strip())
    l = re.sub(r"^[●○■\-]+\s*", "", l)
    l = re.sub(r"^\d+[\.)]\s*", "", l)
    l = re.sub(r"\s+", " ", l)
    return l.strip(" -:")


def _extract_inline_numbered_heading(text: str) -> Optional[str]:
    snippet = re.sub(r"\s+", " ", (text or "").strip())
    if not snippet:
        return None
    match = re.search(r"(?:^|\s)(\d+[\.)]\s+[A-ZÁÉÍÓÚÑ][^\.\n]{4,100})", snippet)
    if not match:
        return None
    raw_heading = match.group(1)
    raw_heading = re.split(r"\s+[●○■]\s+", raw_heading)[0]
    raw_heading = re.split(r"\s{2,}", raw_heading)[0]
    return _normalize_heading(raw_heading)


def _split_sections(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n")
    lines = raw.split("\n")
    blocks: list[str] = []
    current: list[str] = []

    for line in lines:
        stripped = line.strip()

        if _is_page_marker(stripped):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            current.append(stripped)
            continue

        if _is_heading(stripped) and current and len(" ".join(current)) >= 120:
            blocks.append("\n".join(current).strip())
            current = []

        if _is_heading(stripped) and not current:
            current.append(stripped)
            continue

        if not stripped and current:
            # Separa párrafos cuando ya hay tamaño suficiente.
            if len(" ".join(current)) >= 220:
                blocks.append("\n".join(current).strip())
                current = []
            continue

        if stripped:
            current.append(stripped)

    if current:
        blocks.append("\n".join(current).strip())

    return [b for b in blocks if b and len(re.sub(r"\s+", " ", b)) >= 35]


def _clean_chunk_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s*([,;:.])\s*", r"\1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _split_with_page_context(section: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    page_matches = re.findall(r"\[PAGE\s+\d+\]", section)
    page_marker = page_matches[-1] if page_matches else ""
    body = re.sub(r"\[PAGE\s+\d+\]", "", section).strip()
    if not body:
        return []

    base_chunks = _split_long_text(body, chunk_size=chunk_size, overlap=overlap) or [body]
    if not page_marker:
        return [_clean_chunk_text(c) for c in base_chunks if c.strip()]

    out: list[str] = []
    for c in base_chunks:
        t = _clean_chunk_text(c)
        if t:
            out.append(f"{page_marker} {t}")
    return out


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
    current_page: Optional[int] = None
    output: list[dict] = []

    for section in sections:
        lines = [x.strip() for x in section.split("\n") if x.strip()]
        if not lines:
            continue

        non_page_lines = [ln for ln in lines if not _is_page_marker(ln)]
        first_line = non_page_lines[0] if non_page_lines else lines[0]
        inline_heading = _extract_inline_numbered_heading(section)
        if _is_heading(first_line):
            heading = _normalize_heading(first_line)
            if re.match(r"^(tema|unidad|cap[ií]tulo|bloque)\s+\d+", heading, flags=re.I):
                current_theme = heading
                if len(non_page_lines) > 1:
                    current_subtheme = _normalize_heading(non_page_lines[1])
            elif re.match(r"^\d+[\.)]\s+", first_line):
                # En apuntes suele ser un título de bloque principal: 1. Concepto..., 2. Riesgos...
                current_theme = heading
                current_subtheme = heading
            else:
                current_subtheme = heading
        elif inline_heading:
            current_theme = inline_heading
            current_subtheme = inline_heading

        page = _extract_page(section)
        if page is not None:
            current_page = page
        section_type = _detect_content_type(section)
        difficulty = _detect_difficulty(section)

        chunk_candidates = _split_with_page_context(section, chunk_size=chunk_size, overlap=overlap) or [section]
        for text_chunk in chunk_candidates:
            output.append(
                {
                    "text": text_chunk,
                    "metadata": {
                        "asignatura": subject,
                        "tema": current_theme,
                        "subtema": current_subtheme,
                        "tipo_contenido": section_type,
                        "pagina": current_page,
                        "dificultad": difficulty,
                        "fuente": source,
                    },
                }
            )

    return output


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    return _split_long_text(text, chunk_size=chunk_size, overlap=overlap)
