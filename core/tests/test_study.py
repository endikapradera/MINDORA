"""Tests for study.py utility functions (no LLM calls)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.services.study import _extract_section, _extract_list_items


# ---------------------------------------------------------------------------
# _extract_section
# ---------------------------------------------------------------------------

class TestExtractSection:
    SAMPLE = (
        "## RESUMEN_CORTO\n"
        "Este es el resumen corto.\n\n"
        "## RESUMEN_LARGO\n"
        "Este es el resumen largo con más detalle.\n\n"
        "## IDEAS_CLAVE\n"
        "- Idea uno\n"
        "- Idea dos\n"
    )

    def test_first_section(self):
        result = _extract_section(self.SAMPLE, "RESUMEN_CORTO")
        assert "resumen corto" in result.lower()

    def test_middle_section(self):
        result = _extract_section(self.SAMPLE, "RESUMEN_LARGO")
        assert "largo" in result.lower()
        # Should not bleed into IDEAS_CLAVE
        assert "idea" not in result.lower()

    def test_last_section(self):
        result = _extract_section(self.SAMPLE, "IDEAS_CLAVE")
        assert "idea uno" in result.lower()
        assert "idea dos" in result.lower()

    def test_missing_section_returns_empty(self):
        result = _extract_section(self.SAMPLE, "SECCION_INEXISTENTE")
        assert result == ""

    def test_case_insensitive(self):
        lower_sample = self.SAMPLE.lower()
        # Should still work with lowercase header
        result = _extract_section(lower_sample, "resumen_corto")
        assert result != ""


# ---------------------------------------------------------------------------
# _extract_list_items
# ---------------------------------------------------------------------------

class TestExtractListItems:
    def test_bullet_list(self):
        text = "- Concepto uno\n- Concepto dos\n- Concepto tres\n"
        items = _extract_list_items(text)
        assert len(items) == 3
        assert "Concepto uno" in items
        assert "Concepto dos" in items

    def test_numbered_list(self):
        text = "1. Primer elemento\n2. Segundo elemento\n"
        items = _extract_list_items(text)
        assert "Primer elemento" in items
        assert "Segundo elemento" in items

    def test_asterisk_list(self):
        text = "* Alpha\n* Beta\n* Gamma\n"
        items = _extract_list_items(text)
        assert items == ["Alpha", "Beta", "Gamma"]

    def test_empty_lines_skipped(self):
        text = "- Item A\n\n- Item B\n"
        items = _extract_list_items(text)
        assert len(items) == 2

    def test_max_12_items(self):
        text = "\n".join(f"- Item {i}" for i in range(20))
        items = _extract_list_items(text)
        assert len(items) == 12

    def test_plain_paragraph(self):
        text = "Una línea de texto sin viñeta."
        items = _extract_list_items(text)
        assert len(items) == 1
        assert items[0] == "Una línea de texto sin viñeta."


# ---------------------------------------------------------------------------
# generate_study_pack (mocked LLM + retrieval)
# ---------------------------------------------------------------------------

MOCK_RAW = """
## RESUMEN_CORTO
La fotosíntesis es el proceso por el cual las plantas producen glucosa.

## RESUMEN_LARGO
La fotosíntesis ocurre en los cloroplastos. Las plantas capturan luz solar
y CO2 para producir glucosa y oxígeno mediante reacciones de luz y ciclo de Calvin.

## IDEAS_CLAVE
- Las plantas usan clorofila para capturar luz
- El oxígeno es un subproducto
- Ocurre en los cloroplastos

## CONCEPTOS_MEMORIZAR
- Cloroplasto
- Clorofila
- Ciclo de Calvin

## POSIBLES_PREGUNTAS_EXAMEN
- ¿Qué es la fotosíntesis?
- ¿Dónde ocurre la fotosíntesis?

## ERRORES_TIPICOS
- Confundir fotosíntesis con respiración celular
- Creer que la glucosa viene del suelo

## MINI_TEST_5
- Verdadero/Falso: La fotosíntesis ocurre en la mitocondria (FALSO)
- ¿Qué gas producen las plantas? (Oxígeno)
- La clorofila captura _____ (luz solar)
- ¿En qué orgánulo ocurre? (cloroplasto)
- Nombra un subproducto de la fotosíntesis (oxígeno)
"""


class TestGenerateStudyPack:
    def test_all_sections_present(self):
        fake_chunks = [
            {
                "text": "La fotosíntesis es un proceso metabólico.",
                "chunk_id": 1,
                "document_id": 1,
                "score": 0.9,
                "chunk_index": 0,
                "filename": "bio.pdf",
                "path": "/bio.pdf",
            }
        ]

        with patch("app.services.study.retrieve_chunks", return_value=fake_chunks), \
             patch("app.services.study.generate_text", return_value=MOCK_RAW):

            from app.services.study import generate_study_pack
            result = generate_study_pack("test_branch", "fotosíntesis")

        assert result["topic"] == "fotosíntesis"
        assert result["summary_short"] != ""
        assert result["summary_long"] != ""
        assert len(result["key_ideas"]) > 0
        assert len(result["concepts_to_memorize"]) > 0
        assert len(result["possible_exam_questions"]) > 0
        assert len(result["common_mistakes"]) > 0
        assert len(result["mini_test"]) >= 3
        assert "bio.pdf (chunk 0)" in result["sources"]

    def test_no_chunks_raises(self):
        with patch("app.services.study.retrieve_chunks", return_value=[]):
            from app.services.study import generate_study_pack
            with pytest.raises(RuntimeError, match="No hay contexto"):
                generate_study_pack("test_branch", "fotosíntesis")
