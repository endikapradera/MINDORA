"""Tests for simulation utility functions (no LLM, no DB required)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Import private helpers directly
# ---------------------------------------------------------------------------

from app.services.exams import (
    _normalize_choice_letters,
    _normalize_text,
    _development_is_correct,
    _question_topic_hint,
)


# ---------------------------------------------------------------------------
# _normalize_choice_letters
# ---------------------------------------------------------------------------

class TestNormalizeChoiceLetters:
    def test_single_letter(self):
        assert _normalize_choice_letters("A") == {"A"}

    def test_multiple_letters(self):
        result = _normalize_choice_letters("A y B son correctas")
        assert "A" in result
        assert "B" in result

    def test_lowercase_normalized(self):
        assert _normalize_choice_letters("c") == {"C"}

    def test_no_letters_returns_empty(self):
        assert _normalize_choice_letters("123 xyz") == set()

    def test_d_option(self):
        assert _normalize_choice_letters("D") == {"D"}


# ---------------------------------------------------------------------------
# _normalize_text
# ---------------------------------------------------------------------------

class TestNormalizeText:
    def test_lowercases(self):
        assert _normalize_text("HOLA MUNDO") == "hola mundo"

    def test_strips(self):
        assert _normalize_text("  hola  ") == "hola"

    def test_collapses_spaces(self):
        assert _normalize_text("a  b   c") == "a b c"


# ---------------------------------------------------------------------------
# _development_is_correct
# ---------------------------------------------------------------------------

class TestDevelopmentIsCorrect:
    def test_exact_match_returns_true(self):
        text = "la fotosíntesis convierte luz solar en glucosa mediante clorofila"
        assert _development_is_correct(text, text) is True

    def test_completely_wrong_returns_false(self):
        expected = "la fotosíntesis convierte luz solar en glucosa mediante clorofila"
        student = "el agua está compuesta de hidrógeno y oxígeno"
        assert _development_is_correct(expected, student) is False

    def test_partial_overlap_above_threshold(self):
        expected = "fotosíntesis convierte energía solar glucosa clorofila"
        student = "proceso fotosíntesis convierte energía solar clorofila"
        # They share "fotosintesis", "convierte", "energia", "solar", "clorofila" → high overlap
        assert _development_is_correct(expected, student) is True

    def test_empty_student_returns_false(self):
        assert _development_is_correct("algo importante que saber aquí", "") is False

    def test_empty_expected_returns_false(self):
        assert _development_is_correct("", "cualquier respuesta del alumno") is False

    def test_threshold_35_percent(self):
        # Expected has 4 words ≥4 chars, student has exactly 2 matching → 50% → True
        expected = "mitocondria célula energía adenosina"
        student = "mitocondria célula"
        assert _development_is_correct(expected, student) is True

        # Only 1 matching out of 4 → 25% → False
        student_low = "mitocondria bicicleta"
        assert _development_is_correct(expected, student_low) is False


# ---------------------------------------------------------------------------
# _question_topic_hint
# ---------------------------------------------------------------------------

class TestQuestionTopicHint:
    def test_returns_first_words(self):
        result = _question_topic_hint("Qué es la fotosíntesis en las plantas")
        assert isinstance(result, str)
        assert len(result.split()) <= 6

    def test_empty_string_returns_default(self):
        result = _question_topic_hint("")
        assert result == "tema general"

    def test_only_special_chars(self):
        result = _question_topic_hint("??!! ---")
        assert result == "tema general"


# ---------------------------------------------------------------------------
# start / submit simulation (integration test with temp dir)
# ---------------------------------------------------------------------------

class TestSimulationLifecycle:
    """Integration test: mocks branch path to a temp directory."""

    def _make_exam_json(self, tmpdir: Path, exam_id: str) -> None:
        exams_dir = tmpdir / "Exams"
        exams_dir.mkdir(parents=True, exist_ok=True)
        exam = {
            "exam_id": exam_id,
            "topic": "Biología celular",
            "questions": [
                {
                    "number": 1,
                    "type": "test_simple",
                    "statement": "¿Cuál es la función de la mitocondria?",
                    "options": ["A) Digestión", "B) Síntesis de ATP", "C) Fotosíntesis", "D) Reproducción"],
                    "answer": "B",
                    "explanation": "La mitocondria sintetiza ATP.",
                },
                {
                    "number": 2,
                    "type": "desarrollo",
                    "statement": "Explica el ciclo de Krebs.",
                    "options": [],
                    "answer": "El ciclo de Krebs oxida acetil-CoA produciendo NADH y FADH2.",
                    "explanation": "",
                },
            ],
        }
        (exams_dir / f"exam_{exam_id}.json").write_text(
            json.dumps(exam, ensure_ascii=False), encoding="utf-8"
        )

    def test_start_and_submit(self, tmp_path):
        """Full start→submit lifecycle without real DB or LLM."""
        exam_id = "testexam001"
        self._make_exam_json(tmp_path, exam_id)

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True):

            from app.services.exams import start_exam_simulation, submit_exam_simulation

            # Start
            result = start_exam_simulation("test_branch", exam_id, duration_minutes=30)
            assert result["simulation_id"]
            assert result["topic"] == "Biología celular"
            assert len(result["questions"]) == 2
            # Answers should NOT include the correct answer
            for q in result["questions"]:
                assert "answer" not in q

            simulation_id = result["simulation_id"]

            # Submit with correct answer for Q1, partial for Q2
            answers = [
                {"number": 1, "answer": "B"},
                {"number": 2, "answer": "El ciclo de Krebs oxida acetil-CoA produciendo NADH y FADH2."},
            ]
            submit_result = submit_exam_simulation("test_branch", simulation_id, answers)

            assert submit_result["simulation_id"] == simulation_id
            assert submit_result["total_questions"] == 2
            assert submit_result["correct_answers"] >= 1  # Q1 definitely correct
            assert 0.0 <= submit_result["score_percent"] <= 100.0
            assert submit_result["status"] in ("submitted", "timed_out")

    def test_submit_all_wrong(self, tmp_path):
        exam_id = "testexam002"
        self._make_exam_json(tmp_path, exam_id)

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True):

            from app.services.exams import start_exam_simulation, submit_exam_simulation

            result = start_exam_simulation("test_branch", exam_id, duration_minutes=60)
            simulation_id = result["simulation_id"]

            answers = [
                {"number": 1, "answer": "D"},   # wrong
                {"number": 2, "answer": "nada"},  # wrong
            ]
            submit_result = submit_exam_simulation("test_branch", simulation_id, answers)
            assert submit_result["correct_answers"] == 0
            assert submit_result["score_percent"] == 0.0

    def test_history_after_submit(self, tmp_path):
        exam_id = "testexam003"
        self._make_exam_json(tmp_path, exam_id)

        with patch("app.services.exams.get_branch_path", return_value=tmp_path), \
             patch("app.services.exams.branch_exists", return_value=True):

            from app.services.exams import start_exam_simulation, submit_exam_simulation, get_simulation_history

            r = start_exam_simulation("test_branch", exam_id)
            submit_exam_simulation("test_branch", r["simulation_id"], [])

            history = get_simulation_history("test_branch")
            assert history["items"]
            item = history["items"][0]
            assert "simulation_id" in item
            assert "score_percent" in item
            assert "status" in item
