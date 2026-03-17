from __future__ import annotations

import os
import re
import threading
import sys
from typing import Sequence, Literal

from llama_cpp import Llama
from app.services.intent_dictionary import detect_intent_and_style


_LLM_INSTANCE: Llama | None = None
_LLM_LOCK = threading.Lock()


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _should_use_safe_mode() -> bool:
    # macOS + system Python 3.9 + llama-cpp is unstable on this machine.
    if os.getenv("IA_OFFLINE_SAFE_MODE") is not None:
        return _bool_env("IA_OFFLINE_SAFE_MODE")
    return sys.platform == "darwin" and sys.version_info < (3, 10)


def _model_path() -> str:
    path = os.getenv("IA_OFFLINE_LLM_PATH")
    if not path:
        raise RuntimeError("LLM model path not configured. Set IA_OFFLINE_LLM_PATH.")
    return path


def get_llm() -> Llama:
    global _LLM_INSTANCE
    if _LLM_INSTANCE is not None:
        return _LLM_INSTANCE

    with _LLM_LOCK:
        if _LLM_INSTANCE is not None:
            return _LLM_INSTANCE

        path = _model_path()
        n_ctx = int(os.getenv("IA_OFFLINE_LLM_CTX", "2048"))
        n_threads = int(os.getenv("IA_OFFLINE_LLM_THREADS", "1"))
        n_batch = int(os.getenv("IA_OFFLINE_LLM_BATCH", "128"))

        _LLM_INSTANCE = Llama(
            model_path=path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_batch=n_batch,
            verbose=False,
        )
        return _LLM_INSTANCE


def build_prompt(question: str, contexts: list[str]) -> str:
    normalized_q = question.strip().lower()
    if re.match(r"^(explicame|explícame|explica|resumeme|resúmeme|resume|aclara)\s*(esto|eso)?\??$", normalized_q):
        topic_hint = contexts[0][:180].replace("\n", " ") if contexts else "tema del contexto"
        question = f"Explica de forma clara el tema principal del contexto: {topic_hint}"

    detected_intent, detected_style = detect_intent_and_style(question)
    style_rules, _ = _infer_response_style(question)
    if detected_style != "auto":
        selected = _style_from_selector(detected_style)
        if selected is not None:
            style_rules, _ = selected
    context_block = "\n\n".join(contexts)
    return (
        "Eres MINDORA, una IA educativa offline experta en explicar temarios.\n"
        "Reglas estrictas:\n"
        "- Responde SOLO con la información del contexto recuperado.\n"
        "- No inventes datos, leyes, fechas o definiciones.\n"
        "- Si falta información, dilo explícitamente.\n"
        "- Escribe en español claro, estructurado y natural.\n"
        "- Incluye al menos un ejemplo práctico cuando sea posible.\n"
        "- Cita al final las fuentes usadas usando etiquetas [FUENTE n] del contexto.\n"
        f"Intención detectada del usuario: {detected_intent}.\n"
        f"Formato de respuesta:\n{style_rules}\n\n"
        f"Contexto:\n{context_block}\n\n"
        f"Pregunta: {question}\n"
        "Respuesta:"
    )


def _infer_response_style(question: str) -> tuple[str, int]:
    q = question.lower()
    wants_short = any(k in q for k in ["corta", "corto", "breve", "resumen corto", "en pocas palabras"])
    wants_detailed = any(k in q for k in ["detallada", "detallado", "profunda", "completa", "a fondo"])
    wants_steps = any(k in q for k in ["por pasos", "paso a paso", "en pasos"])

    if wants_short:
        if wants_steps:
            rules = "- Máximo 6 líneas.\n- Explica en 3 pasos numerados.\n- Incluye 1 mini ejemplo final."
        else:
            rules = "- Máximo 6 líneas.\n- Resumen directo y claro.\n- Sin rodeos ni repeticiones."
        return rules, 180

    if wants_detailed:
        if wants_steps:
            rules = (
                "1) Resumen inicial (2-3 líneas).\n"
                "2) Explicación detallada por pasos numerados.\n"
                "3) Ejemplo práctico aplicado.\n"
                "4) Cierre con errores comunes a evitar."
            )
        else:
            rules = (
                "1) Resumen inicial (2-3 líneas).\n"
                "2) Explicación clara y completa.\n"
                "3) Ejemplo práctico aplicado.\n"
                "4) Idea clave final."
            )
        return rules, 700

    if wants_steps:
        rules = "1) Resumen corto.\n2) Explicación paso a paso numerada.\n3) Ejemplo breve aplicado."
        return rules, 500

    default_rules = "1) Resumen corto.\n2) Explicación clara.\n3) Ejemplo breve aplicado."
    return default_rules, 450


def _style_from_selector(style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos"]) -> tuple[str, int] | None:
    if style == "corta":
        return "- Máximo 6 líneas.\n- Resumen directo y claro.\n- Sin rodeos ni repeticiones.", 180
    if style == "detallada":
        return (
            "1) Resumen inicial (2-3 líneas).\n"
            "2) Explicación clara y completa.\n"
            "3) Ejemplo práctico aplicado.\n"
            "4) Idea clave final.",
            700,
        )
    if style == "pasos":
        return "1) Resumen corto.\n2) Explicación paso a paso numerada.\n3) Ejemplo breve aplicado.", 500
    if style == "detallada_pasos":
        return (
            "1) Resumen inicial (2-3 líneas).\n"
            "2) Explicación detallada por pasos numerados.\n"
            "3) Ejemplo práctico aplicado.\n"
            "4) Cierre con errores comunes a evitar.",
            700,
        )
    return None


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [p.strip() for p in parts if p.strip()]


def _clean_extractive_text(text: str) -> str:
    text = re.sub(r"©\s*Copyright[^\.\n]*", "", text, flags=re.I)
    text = re.sub(r"\b\d{1,3}\s*/\s*\d{1,2}/\d{2,4}\b", "", text)
    text = re.sub(r"\b\d{2,4}\b(?=\s*$)", "", text)
    text = re.sub(r"[•·]+", ". ", text)
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return text


def _rank_sentences(question: str, sentences: list[str]) -> list[str]:
    q_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", question.lower()))
    scored: list[tuple[int, int, str]] = []
    for i, sentence in enumerate(sentences):
        cleaned = _clean_extractive_text(sentence)
        if len(cleaned) < 25:
            continue
        s_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", cleaned.lower()))
        overlap = len(q_tokens.intersection(s_tokens))
        scored.append((overlap, -i, cleaned))
    scored.sort(reverse=True)
    ranked = [text for _, _, text in scored if text]
    return ranked or [_clean_extractive_text(s) for s in sentences]


def generate_answer_fallback(
    question: str,
    contexts: list[str],
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos"] = "auto",
) -> str:
    """Deterministic extractive fallback used when local LLM is unstable/unavailable."""
    if not contexts:
        return "No encontré información suficiente en el contexto para responder."

    merged = "\n\n".join(contexts[:3])
    sentences = _split_sentences(merged)
    if not sentences:
        return contexts[0][:700]
    ranked = _rank_sentences(question, sentences)

    q = question.lower()
    wants_steps = response_style in {"pasos", "detallada_pasos"} or "paso a paso" in q or "fácil" in q
    wants_short = response_style == "corta" or "1 minuto" in q or "resumen" in q

    if wants_short:
        selected = ranked[:3]
        return "\n".join(f"- {s}" for s in selected)

    if wants_steps:
        selected = ranked[:4]
        return "\n".join(f"{i + 1}) {s}" for i, s in enumerate(selected))

    selected = ranked[:5]
    return "\n".join(selected)


def generate_text(prompt: str, max_tokens: int = 400, temperature: float = 0.2, stop: Sequence[str] | None = None) -> str:
    llm = get_llm()
    output = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=0.9,
        stop=list(stop) if stop else None,
    )
    return output["choices"][0]["text"].strip()


def _dedupe_lines(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for line in text.splitlines():
        key = re.sub(r"\s+", " ", line.strip().lower())
        if not key:
            output.append(line)
            continue
        if key in seen:
            continue
        seen.add(key)
        output.append(line)
    return "\n".join(output).strip()


def generate_answer(
    question: str,
    contexts: list[str],
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos"] = "auto",
    history: list[dict] | None = None,
) -> str:
    if _should_use_safe_mode():
        return generate_answer_fallback(question, contexts, response_style)

    detected_intent, detected_style = detect_intent_and_style(question)
    effective_style = response_style if response_style != "auto" else detected_style

    selected = _style_from_selector(effective_style)
    if selected is None:
        style_rules, max_tokens = _infer_response_style(question)
    else:
        style_rules, max_tokens = selected

    normalized_q = question.strip().lower()
    if re.match(r"^(explicame|explícame|explica|resumeme|resúmeme|resume|aclara)\s*(esto|eso)?\??$", normalized_q):
        topic_hint = contexts[0][:180].replace("\n", " ") if contexts else "tema del contexto"
        question = f"Explica de forma clara el tema principal del contexto: {topic_hint}"

    context_block = "\n\n".join(contexts)
    history_block = ""
    if history:
        turns: list[str] = []
        for msg in history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                turns.append(f"{role.upper()}: {content}")
        if turns:
            history_block = "\n\nHistorial reciente:\n" + "\n".join(turns)

    prompt = (
        "Eres MINDORA, una IA educativa offline experta en explicar temarios.\n"
        "Reglas estrictas:\n"
        "- Responde SOLO con la información del contexto recuperado.\n"
        "- No inventes datos, leyes, fechas o definiciones.\n"
        "- Si falta información, dilo explícitamente.\n"
        "- Escribe en español claro, estructurado y natural.\n"
        "- Incluye al menos un ejemplo práctico cuando sea posible.\n"
        "- Cita al final las fuentes usadas usando etiquetas [FUENTE n] del contexto.\n"
        f"Intención detectada del usuario: {detected_intent}.\n"
        f"Formato de respuesta:\n{style_rules}\n\n"
        f"Contexto:\n{context_block}\n\n"
        f"{history_block}\n\n"
        f"Pregunta: {question}\n"
        "Respuesta:"
    )
    raw = generate_text(prompt, max_tokens=max_tokens, temperature=0.15, stop=["\n\nPregunta:"])
    return _dedupe_lines(raw)
