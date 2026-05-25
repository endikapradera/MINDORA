from __future__ import annotations

import os
from typing import Literal

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

ResponseStyle = Literal[
    "auto",
    "corta",
    "detallada",
    "pasos",
    "detallada_pasos",
    "examen",
    "profesor",
    "companero",
    "codigo",
]


def _provider() -> str:
    return os.getenv("IA_LOCAL_LLM_PROVIDER", "ollama").strip().lower()


def _base_url() -> str:
    env_url = os.getenv("IA_LOCAL_LLM_BASE_URL", "").strip()
    if env_url:
        return env_url.rstrip("/")

    provider = _provider()
    if provider == "lmstudio":
        return "http://127.0.0.1:1234/v1"
    return "http://127.0.0.1:11434/v1"


def _api_key() -> str:
    # For local OpenAI-compatible servers (Ollama / LM Studio), any non-empty key works.
    return os.getenv("IA_LOCAL_LLM_API_KEY", "local-dev")


def _model() -> str:
    provider = _provider()
    if provider == "lmstudio":
        return os.getenv("IA_LOCAL_LLM_MODEL", "qwen2.5-7b-instruct")
    return os.getenv("IA_LOCAL_LLM_MODEL", "qwen2.5:7b")


def _style_rules(response_style: ResponseStyle) -> str:
    rules: dict[ResponseStyle, str] = {
        "auto": "Responde de forma clara y estructurada en 2-4 párrafos, con viñetas si ayuda.",
        "corta": "Respuesta breve: máximo 6 líneas y una mini conclusión.",
        "detallada": "Respuesta completa: contexto, desarrollo, ejemplo y cierre.",
        "pasos": "Responde en pasos numerados, del más básico al más práctico.",
        "detallada_pasos": "Respuesta larga organizada en pasos con explicaciones de cada paso.",
        "examen": "Formato examen: definición, puntos clave y cierre evaluable.",
        "profesor": "Tono docente: explicación clara, ejemplo guiado y pregunta de comprobación.",
        "companero": "Tono cercano, sencillo y directo, sin perder precisión.",
        "codigo": "Devuelve explicación técnica y, si procede, bloque de código corregido o mejorado.",
    }
    return rules.get(response_style, rules["auto"])


def _history_text(history: list[dict] | None) -> str:
    if not history:
        return ""

    turns: list[str] = []
    for msg in history[-8:]:
        role = str(msg.get("role", "user")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        role_label = "USUARIO" if role == "user" else "ASISTENTE"
        turns.append(f"{role_label}: {content}")

    if not turns:
        return ""
    return "\n".join(turns)


def generate_answer_langchain(
    question: str,
    contexts: list[str],
    response_style: ResponseStyle = "auto",
    history: list[dict] | None = None,
) -> str:
    """Generate answers through LangChain using a local OpenAI-compatible endpoint.

    Compatible with:
    - Ollama server (`http://127.0.0.1:11434/v1`)
    - LM Studio server (`http://127.0.0.1:1234/v1`)
    """
    if not contexts:
        return "No encontré información suficiente en el contexto para responder."

    llm = ChatOpenAI(
        model=_model(),
        base_url=_base_url(),
        api_key=_api_key(),
        temperature=float(os.getenv("IA_LOCAL_LLM_TEMPERATURE", "0.05")),
        max_tokens=int(os.getenv("IA_LOCAL_LLM_MAX_TOKENS", "850")),
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres MINDORA, asistente educativo offline especializado en ofrecer respuestas precisas y académicamente rigurosas. "
                "REGLAS CRÍTICAS:\n"
                "1. Usa ÚNICAMENTE la información del CONTEXTO recuperado. No inventes, no especules.\n"
                "2. Si el contexto no tiene suficiente información, dilo explícitamente.\n"
                "3. Sé muy específico: cita conceptos, definiciones exactas y fuentes del contexto.\n"
                "4. Estructura lógicamente: primero lo fundamental, luego detalles, al final aplicación.\n"
                "5. Evita respuestas genéricas o superficiales - profundiza en los conceptos.\n"
                "6. Usa ejemplos concretos del contexto cuando sea posible.\n"
                "7. Distingue entre definiciones académicas, procedimientos, e interpretaciones.",
            ),
            (
                "human",
                "ESTILO DE RESPUESTA:\n{style_rules}\n\n"
                "CONTEXTO FIABLE:\n{context}\n\n"
                "HISTORIAL (para continuidad):\n{history}\n\n"
                "PREGUNTA DEL USUARIO:\n{question}\n\n"
                "Instrucciones finales:\n"
                "- Responde basándote únicamente en el contexto.\n"
                "- Si necesitas aclarar algo del contexto, hazlo.\n"
                "- Estructura con claridad: resumen breve, puntos clave y cierre.\n"
                "- Cita al final 2-4 referencias de evidencia usando formato [FUENTE n].\n"
                "- Omite rodeos innecesarios y evita repetir frases."
            ),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke(
        {
            "style_rules": _style_rules(response_style),
            "context": "\n\n".join(contexts),
            "history": _history_text(history),
            "question": question,
        }
    )

    text = (answer or "").strip()
    if not text:
        return "No pude generar una respuesta en este momento con el modelo local."
    return text
