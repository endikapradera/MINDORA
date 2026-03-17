"""Tests for intent_dictionary service (no LLM, no DB required)."""
from __future__ import annotations

import pytest
from app.services.intent_dictionary import (
    DEFAULT_ENTRIES,
    detect_intent_and_style,
    add_dictionary_entry,
    remove_dictionary_entry,
    list_dictionary_entries,
    load_custom_entries,
    phrase_from_question,
    _normalize,
)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_strips_whitespace(self):
        assert _normalize("  hola  ") == "hola"

    def test_collapses_spaces(self):
        assert _normalize("a   b   c") == "a b c"

    def test_lowercases(self):
        assert _normalize("EXPLÍCAME") == "explícame"


# ---------------------------------------------------------------------------
# DEFAULT_ENTRIES structure
# ---------------------------------------------------------------------------

class TestDefaultEntries:
    def test_not_empty(self):
        assert len(DEFAULT_ENTRIES) > 10

    def test_all_have_required_keys(self):
        for entry in DEFAULT_ENTRIES:
            assert "phrase" in entry, f"Missing 'phrase': {entry}"
            assert "intent" in entry, f"Missing 'intent': {entry}"
            assert "response_style" in entry, f"Missing 'response_style': {entry}"

    def test_valid_styles(self):
        valid_styles = {"auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"}
        for entry in DEFAULT_ENTRIES:
            assert entry["response_style"] in valid_styles, (
                f"Invalid style '{entry['response_style']}' in {entry}"
            )

    def test_valid_intents(self):
        valid_intents = {"explicar", "resumir", "comparar", "ejemplo", "definir", "pasos", "general"}
        for entry in DEFAULT_ENTRIES:
            assert entry["intent"] in valid_intents, (
                f"Invalid intent '{entry['intent']}' in {entry}"
            )


# ---------------------------------------------------------------------------
# detect_intent_and_style – known phrases
# ---------------------------------------------------------------------------

class TestDetectIntentAndStyle:
    @pytest.mark.parametrize("question,expected_intent,expected_style", [
        ("explícamelo fácil esto", "explicar", "pasos"),
        ("resumen corto del tema", "resumir", "corta"),
        ("paso a paso cómo funciona", "pasos", "pasos"),
        ("pon un ejemplo de esto", "ejemplo", "auto"),
        ("modo examen activa", "general", "examen"),
        ("mini test sobre el tema", "general", "detallada_pasos"),
        ("explicamelo en 1 minuto", "resumir", "corta"),
        ("define el concepto", "definir", "auto"),
        ("diferencia entre A y B", "comparar", "auto"),
        ("no entiendo esto", "explicar", "pasos"),
    ])
    def test_known_phrases(self, question, expected_intent, expected_style):
        intent, style = detect_intent_and_style(question)
        assert intent == expected_intent, f"Q='{question}' → intent={intent!r}, expected={expected_intent!r}"
        assert style == expected_style, f"Q='{question}' → style={style!r}, expected={expected_style!r}"

    def test_unknown_question_returns_general_auto(self):
        intent, style = detect_intent_and_style("cuáles son los planetas del sistema solar")
        assert intent == "general"
        assert style == "auto"

    def test_longer_phrase_wins_over_shorter(self):
        """'explícamelo fácil' should win over bare 'explícame'."""
        intent, style = detect_intent_and_style("explícamelo fácil esto")
        assert style == "pasos"  # not "auto" which is what bare "explicame" gives


# ---------------------------------------------------------------------------
# phrase_from_question
# ---------------------------------------------------------------------------

class TestPhraseFromQuestion:
    def test_short_question(self):
        result = phrase_from_question("Qué es la fotosíntesis")
        assert isinstance(result, str)
        assert len(result.split()) <= 7

    def test_long_question_truncated(self):
        long_q = "cuáles son las principales características del reino animal en biología"
        result = phrase_from_question(long_q, max_words=5)
        assert len(result.split()) <= 5

    def test_empty_string(self):
        result = phrase_from_question("")
        assert result == ""


# ---------------------------------------------------------------------------
# add / remove custom entries
# ---------------------------------------------------------------------------

class TestCustomEntries:
    """These tests manipulate the on-disk phrase_dictionary.json.
    Each test cleans up the phrase it adds to keep tests isolated."""

    TEST_PHRASE = "__pytest_test_phrase__"

    def teardown_method(self):
        """Always remove the test phrase after each test."""
        try:
            remove_dictionary_entry(self.TEST_PHRASE)
        except Exception:
            pass

    def test_add_and_detect(self):
        add_dictionary_entry(self.TEST_PHRASE, "ejemplo", "detallada")
        entries = list_dictionary_entries()
        phrases = [e["phrase"] for e in entries]
        assert self.TEST_PHRASE in phrases

    def test_add_then_remove(self):
        add_dictionary_entry(self.TEST_PHRASE, "resumir", "corta")
        remove_dictionary_entry(self.TEST_PHRASE)
        custom = load_custom_entries()
        phrases = [_normalize(e["phrase"]) for e in custom]
        assert _normalize(self.TEST_PHRASE) not in phrases

    def test_add_duplicate_overwrites(self):
        add_dictionary_entry(self.TEST_PHRASE, "explicar", "auto")
        add_dictionary_entry(self.TEST_PHRASE, "definir", "pasos")
        custom = load_custom_entries()
        matches = [e for e in custom if _normalize(e["phrase"]) == _normalize(self.TEST_PHRASE)]
        assert len(matches) == 1
        assert matches[0]["intent"] == "definir"
