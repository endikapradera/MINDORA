from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from app.storage.config import get_base_dir

ResponseStyle = Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"]
IntentType = Literal["explicar", "resumir", "comparar", "ejemplo", "definir", "pasos", "general"]

DEFAULT_ENTRIES: list[dict] = [
    {"phrase": "explicame", "intent": "explicar", "response_style": "auto"},
    {"phrase": "explícame", "intent": "explicar", "response_style": "auto"},
    {"phrase": "explicamelo fácil", "intent": "explicar", "response_style": "pasos"},
    {"phrase": "explícamelo fácil", "intent": "explicar", "response_style": "pasos"},
    {"phrase": "explícamelo como si fuera examen", "intent": "explicar", "response_style": "detallada_pasos"},
    {"phrase": "explicamelo con ejemplos", "intent": "ejemplo", "response_style": "detallada"},
    {"phrase": "explicamelo paso a paso", "intent": "pasos", "response_style": "pasos"},
    {"phrase": "explicamelo en 1 minuto", "intent": "resumir", "response_style": "corta"},
    {"phrase": "resumeme", "intent": "resumir", "response_style": "corta"},
    {"phrase": "resúmeme", "intent": "resumir", "response_style": "corta"},
    {"phrase": "resumen corto", "intent": "resumir", "response_style": "corta"},
    {"phrase": "resumen largo", "intent": "explicar", "response_style": "detallada"},
    {"phrase": "ideas clave", "intent": "resumir", "response_style": "corta"},
    {"phrase": "conceptos que memorizar", "intent": "definir", "response_style": "pasos"},
    {"phrase": "posibles preguntas de examen", "intent": "general", "response_style": "detallada_pasos"},
    {"phrase": "errores típicos", "intent": "general", "response_style": "pasos"},
    {"phrase": "errores tipicos", "intent": "general", "response_style": "pasos"},
    {"phrase": "no entiendo esto", "intent": "explicar", "response_style": "pasos"},
    {"phrase": "versión fácil", "intent": "explicar", "response_style": "pasos"},
    {"phrase": "version facil", "intent": "explicar", "response_style": "pasos"},
    {"phrase": "versión técnica", "intent": "definir", "response_style": "detallada"},
    {"phrase": "version tecnica", "intent": "definir", "response_style": "detallada"},
    {"phrase": "analogía", "intent": "ejemplo", "response_style": "auto"},
    {"phrase": "analogia", "intent": "ejemplo", "response_style": "auto"},
    {"phrase": "esquema", "intent": "pasos", "response_style": "pasos"},
    {"phrase": "modo examen", "intent": "general", "response_style": "examen"},
    {"phrase": "como examen", "intent": "general", "response_style": "examen"},
    {"phrase": "modo profesor", "intent": "explicar", "response_style": "profesor"},
    {"phrase": "explícalo como profesor", "intent": "explicar", "response_style": "profesor"},
    {"phrase": "explicalo como profesor", "intent": "explicar", "response_style": "profesor"},
    {"phrase": "modo compañero", "intent": "explicar", "response_style": "companero"},
    {"phrase": "modo companero", "intent": "explicar", "response_style": "companero"},
    {"phrase": "explícalo como compañero", "intent": "explicar", "response_style": "companero"},
    {"phrase": "explicalo como companero", "intent": "explicar", "response_style": "companero"},
    {"phrase": "mini test", "intent": "general", "response_style": "detallada_pasos"},
    {"phrase": "verdadero o falso", "intent": "general", "response_style": "pasos"},
    {"phrase": "repaso rápido", "intent": "resumir", "response_style": "corta"},
    {"phrase": "repaso rapido", "intent": "resumir", "response_style": "corta"},
    {"phrase": "respuesta corta", "intent": "resumir", "response_style": "corta"},
    {"phrase": "respuesta detallada", "intent": "explicar", "response_style": "detallada"},
    {"phrase": "por pasos", "intent": "pasos", "response_style": "pasos"},
    {"phrase": "paso a paso", "intent": "pasos", "response_style": "pasos"},
    {"phrase": "detallada por pasos", "intent": "pasos", "response_style": "detallada_pasos"},
    {"phrase": "pon un ejemplo", "intent": "ejemplo", "response_style": "auto"},
    {"phrase": "define", "intent": "definir", "response_style": "auto"},
    {"phrase": "diferencia", "intent": "comparar", "response_style": "auto"},
]


def _dictionary_path() -> Path:
    return get_base_dir() / "phrase_dictionary.json"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def load_custom_entries() -> list[dict]:
    path = _dictionary_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("entries", [])


def save_custom_entries(entries: list[dict]) -> None:
    path = _dictionary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_dictionary_entries() -> list[dict]:
    return DEFAULT_ENTRIES + load_custom_entries()


def add_dictionary_entry(phrase: str, intent: IntentType, response_style: ResponseStyle) -> None:
    normalized_phrase = _normalize(phrase)
    custom = load_custom_entries()
    custom = [e for e in custom if _normalize(e.get("phrase", "")) != normalized_phrase]
    custom.append({"phrase": phrase, "intent": intent, "response_style": response_style})
    save_custom_entries(custom)


def remove_dictionary_entry(phrase: str) -> None:
    normalized_phrase = _normalize(phrase)
    custom = load_custom_entries()
    custom = [e for e in custom if _normalize(e.get("phrase", "")) != normalized_phrase]
    save_custom_entries(custom)


def phrase_from_question(question: str, max_words: int = 7) -> str:
    words = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]+", question.lower())
    if not words:
        return question.strip()
    return " ".join(words[:max_words]).strip()


def detect_intent_and_style(question: str) -> tuple[IntentType, ResponseStyle]:
    q = _normalize(question)
    entries = sorted(
        list_dictionary_entries(),
        key=lambda e: len(_normalize(e.get("phrase", ""))),
        reverse=True,
    )
    for entry in entries:
        phrase = _normalize(entry.get("phrase", ""))
        if not phrase:
            continue
        if phrase in q:
            intent = entry.get("intent", "general")
            style = entry.get("response_style", "auto")
            return intent, style
    return "general", "auto"
