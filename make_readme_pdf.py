#!/usr/bin/env python3
"""Convierte README.md a README.pdf con estilo profesional."""
from __future__ import annotations
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

README_PATH = Path(__file__).parent / "README.md"
OUTPUT_PATH = Path(__file__).parent / "README.pdf"

# ── Colores ──────────────────────────────────────────────────────────────────
C_BG       = colors.HexColor("#0f172a")
C_PRIMARY  = colors.HexColor("#2563eb")
C_ACCENT   = colors.HexColor("#60a5fa")
C_TEXT     = colors.HexColor("#1e293b")
C_SUBTEXT  = colors.HexColor("#475569")
C_CODE_BG  = colors.HexColor("#1e293b")
C_CODE_FG  = colors.HexColor("#f1f5f9")
C_TH_BG    = colors.HexColor("#1e3a8a")
C_TH_FG    = colors.white
C_TD_BG    = colors.HexColor("#f0f7ff")
C_BORDER   = colors.HexColor("#bfdbfe")

W, H = A4
MARGIN = 1.7 * cm

def build_styles():
    base = getSampleStyleSheet()
    s = {}

    s["h1"] = ParagraphStyle("h1",
        fontName="Helvetica-Bold", fontSize=22, leading=28,
        textColor=C_PRIMARY, spaceAfter=10, spaceBefore=4, alignment=TA_LEFT)
    s["h2"] = ParagraphStyle("h2",
        fontName="Helvetica-Bold", fontSize=15, leading=20,
        textColor=C_PRIMARY, spaceAfter=6, spaceBefore=14, borderPadding=(0,0,4,0))
    s["h3"] = ParagraphStyle("h3",
        fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=C_TEXT, spaceAfter=4, spaceBefore=10)
    s["body"] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9.5, leading=14,
        textColor=C_TEXT, spaceAfter=4, alignment=TA_LEFT)
    s["blockquote"] = ParagraphStyle("blockquote",
        fontName="Helvetica-Oblique", fontSize=9.5, leading=14,
        textColor=C_SUBTEXT, spaceAfter=6, leftIndent=18,
        borderPadding=6, backColor=colors.HexColor("#f0f7ff"),
        borderColor=C_PRIMARY, borderWidth=3, borderRadius=4)
    s["bullet"] = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9.5, leading=14,
        textColor=C_TEXT, leftIndent=18, bulletIndent=6, spaceAfter=2)
    s["code"] = ParagraphStyle("code",
        fontName="Courier", fontSize=8.5, leading=12,
        textColor=C_CODE_FG, backColor=C_CODE_BG, spaceAfter=6,
        leftIndent=8, rightIndent=8, borderPadding=8, borderRadius=4)
    s["caption"] = ParagraphStyle("caption",
        fontName="Helvetica", fontSize=8, textColor=C_SUBTEXT,
        spaceAfter=2, spaceBefore=2, alignment=TA_CENTER)
    return s

def _escape(text: str) -> str:
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))

def _inline_fmt(text: str, style_name: str = "body") -> str:
    """Convert **bold**, `code` and [link](url) inline markdown."""
    text = _escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" color="#2563eb">\1</font>', text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r'<u>\1</u>', text)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    return text

def parse_md_to_flowables(md: str, styles: dict) -> list:
    flowables = []
    lines = md.splitlines()
    i = 0
    in_code = False
    code_lines: list[str] = []

    while i < len(lines):
        line = lines[i]

        # ── Code block ──────────────────────────────────────────────────────
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_lines = []
            else:
                in_code = False
                code_text = "\n".join(code_lines)
                flowables.append(Preformatted(code_text, styles["code"]))
                flowables.append(Spacer(1, 0.2*cm))
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        stripped = line.strip()

        # ── Skip raw HTML (images etc.) ─────────────────────────────────────
        if stripped.startswith("<"):
            i += 1
            continue

        # ── Headings ────────────────────────────────────────────────────────
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            flowables.append(Spacer(1, 0.3*cm))
            flowables.append(Paragraph(_inline_fmt(text), styles["h1"]))
            flowables.append(HRFlowable(width="100%", thickness=2, color=C_PRIMARY, spaceAfter=8))
            i += 1
            continue

        if stripped.startswith("## "):
            text = stripped[3:].strip()
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            flowables.append(Spacer(1, 0.2*cm))
            flowables.append(Paragraph(_inline_fmt(text), styles["h2"]))
            flowables.append(HRFlowable(width="100%", thickness=0.8, color=C_ACCENT, spaceAfter=6))
            i += 1
            continue

        if stripped.startswith("### "):
            text = stripped[4:].strip()
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            flowables.append(Paragraph(_inline_fmt(text), styles["h3"]))
            i += 1
            continue

        # ── Horizontal rule ─────────────────────────────────────────────────
        if stripped in ("---", "___", "***"):
            flowables.append(Spacer(1, 0.15*cm))
            flowables.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
            flowables.append(Spacer(1, 0.15*cm))
            i += 1
            continue

        # ── Blockquote ───────────────────────────────────────────────────────
        if stripped.startswith("> "):
            text = stripped[2:].strip()
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            flowables.append(Paragraph(_inline_fmt(text), styles["blockquote"]))
            i += 1
            continue

        # ── Table ────────────────────────────────────────────────────────────
        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            rows = []
            for tl in table_lines:
                if re.match(r"^\|[-| :]+\|$", tl):
                    continue
                cells = [c.strip() for c in tl.strip("|").split("|")]
                rows.append(cells)
            if rows:
                col_count = max(len(r) for r in rows)
                norm = [r + [""] * (col_count - len(r)) for r in rows]
                # Style header vs body
                tbl_data = []
                for ri, row in enumerate(norm):
                    tbl_data.append([
                        Paragraph(_inline_fmt(cell),
                            ParagraphStyle("th" if ri == 0 else "td",
                                fontName="Helvetica-Bold" if ri == 0 else "Helvetica",
                                fontSize=8.5, leading=12,
                                textColor=C_TH_FG if ri == 0 else C_TEXT))
                        for cell in row
                    ])
                col_w = (W - 2 * MARGIN) / col_count
                t = Table(tbl_data, colWidths=[col_w] * col_count, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), C_TH_BG),
                    ("BACKGROUND", (0, 1), (-1, -1), C_TD_BG),
                    ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, C_TD_BG]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]))
                flowables.append(t)
                flowables.append(Spacer(1, 0.3*cm))
            continue

        # ── Bullet list ───────────────────────────────────────────────────────
        if re.match(r"^[-*•]\s+", stripped):
            text = re.sub(r"^[-*•]\s+", "", stripped)
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            flowables.append(Paragraph("• " + _inline_fmt(text), styles["bullet"]))
            i += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            text = re.sub(r"^\d+\.\s+", "", stripped)
            text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", text)
            match = re.match(r"^(\d+)\.", stripped)
            num = match.group(1) if match else "•"
            flowables.append(Paragraph(f"{num}. " + _inline_fmt(text), styles["bullet"]))
            i += 1
            continue

        # ── Empty line ───────────────────────────────────────────────────────
        if not stripped:
            flowables.append(Spacer(1, 0.18*cm))
            i += 1
            continue

        # ── Regular paragraph ─────────────────────────────────────────────────
        text = re.sub(r"^[🔍📚🤖💾📝💬🗑🛠✨📄💡📋🎨✅🧠📷🐛⬆️🔍🏗🚀📦🗂]+\s*", "", stripped)
        if text:
            flowables.append(Paragraph(_inline_fmt(text), styles["body"]))
        i += 1

    return flowables

def build_cover(styles) -> list:
    items = []
    items.append(Spacer(1, 2.5 * cm))
    items.append(Paragraph("MINDORA", ParagraphStyle("cover_title",
        fontName="Helvetica-Bold", fontSize=42, leading=50,
        textColor=C_PRIMARY, alignment=TA_CENTER, spaceAfter=8)))
    items.append(Paragraph("IA Educativa Offline", ParagraphStyle("cover_sub",
        fontName="Helvetica", fontSize=20, leading=26,
        textColor=C_SUBTEXT, alignment=TA_CENTER, spaceAfter=6)))
    items.append(HRFlowable(width="60%", thickness=2, color=C_PRIMARY, spaceAfter=20))
    items.append(Paragraph(
        "Aplicación de escritorio para uso estudiantil gratuito.<br/>"
        "Sube apuntes, genera exámenes, pregunta y estudia.<br/>"
        "Todo funciona <b>sin internet</b> una vez instalada.",
        ParagraphStyle("cover_desc",
            fontName="Helvetica", fontSize=11.5, leading=18,
            textColor=C_TEXT, alignment=TA_CENTER, spaceAfter=30)))
    items.append(Spacer(1, 1 * cm))
    items.append(Paragraph("Desarrollado por <b>Endika Pradera Touzani</b> · Marzo 2026",
        ParagraphStyle("cover_author",
            fontName="Helvetica", fontSize=9.5,
            textColor=C_SUBTEXT, alignment=TA_CENTER)))
    items.append(Spacer(1, 3 * cm))
    items.append(HRFlowable(width="100%", thickness=1.5, color=C_BORDER))
    items.append(Spacer(1, 0.5 * cm))
    return items

def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_SUBTEXT)
    canvas.drawRightString(W - MARGIN, 0.9 * cm, f"MINDORA — Página {doc.page}")
    canvas.drawString(MARGIN, 0.9 * cm, "IA Educativa Offline · github.com/endikapradera/MINDORA")
    canvas.restoreState()

def main():
    md = README_PATH.read_text(encoding="utf-8")
    styles = build_styles()

    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=1.6 * cm,
        title="MINDORA — IA Educativa Offline",
        author="Endika Pradera Touzani",
        subject="Documentación técnica MINDORA",
    )

    story = build_cover(styles) + parse_md_to_flowables(md, styles)
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(f"✅ PDF generado: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
