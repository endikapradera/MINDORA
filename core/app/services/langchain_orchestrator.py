from __future__ import annotations

import os
import re
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
        "auto": "Responde de forma clara y estructurada en 3-5 párrafos, con viñetas solo si realmente ayudan a la claridad. "
                "Inicia con una idea principal, desarrolla con ejemplos y cierra con síntesis.",
        "corta": "Respuesta concisa pero completa: máximo 5-6 líneas. Dicho directo, sin rodeos, pero manteniendo precisión.",
        "detallada": "Respuesta exhaustiva: introducción, contexto histórico/conceptual, desarrollo profundo con ejemplos concretos, "
                    "implicaciones, y conclusión educativa. Mínimo 4-5 párrafos bien desarrollados.",
        "pasos": "Estructura en pasos numerados progresivos, de lo más básico a lo más avanzado. Cada paso con explicación clara "
                "y transición natural al siguiente.",
        "detallada_pasos": "Respuesta extensa dividida en secciones numeradas. Cada sección: teoría, ejemplo, y aplicación. "
                          "Mínimo 6-8 pasos con profundidad académica.",
        "examen": "Formato tipo pregunta de examen: (1) Definición exacta, (2) Puntos clave diferenciados, (3) Ejemplos distintos, "
                 "(4) Conclusión evaluable. Usa bullet points para claridad.",
        "profesor": "Tono socrático y docente: explica el 'qué' y el 'por qué', proporciona ejemplo guiado paso a paso, "
                   "y termina con una pregunta reflexiva para el estudiante.",
        "companero": "Tono conversacional pero riguroso: como si un compañero experto te lo explicara directamente. Natural, "
                    "sencillo, sin ser superficial. Personaje amable y accesible.",
        "codigo": "Respuesta técnica con bloque de código si es necesario. Explicación clara + implementación + casos de uso + "
                 "notas de seguridad o performance.",
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


def _question_tokens(text: str) -> set[str]:
    stopwords = {
        "para", "como", "este", "esta", "estos", "estas", "desde", "sobre", "entre", "porque",
        "donde", "cuando", "quien", "cual", "cuales", "explica", "explicame", "explícame", "hazme",
        "resumen", "resumeme", "resúmeme", "tema", "tema", "todo", "toda", "general", "quiero",
        "puedes", "podrias", "podrías", "del", "las", "los", "una", "unos", "unas", "qué", "que",
    }
    raw = re.findall(r"[a-záéíóúñ0-9]{3,}", (text or "").lower())
    return {tok for tok in raw if tok not in stopwords}


def _split_context_entry(entry: str) -> tuple[str, str]:
    parts = entry.split("\n", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "[FUENTE ?]", entry.strip()


def _sentence_score(sentence: str, q_tokens: set[str]) -> float:
    sentence_tokens = set(re.findall(r"[a-záéíóúñ0-9]{3,}", sentence.lower()))
    if not sentence_tokens:
        return 0.0
    overlap = len(sentence_tokens & q_tokens)
    density = overlap / max(1, len(sentence_tokens))
    length_bonus = min(len(sentence) / 220.0, 1.0)
    return overlap * 2.0 + density + length_bonus


def _build_evidence_digest(question: str, contexts: list[str], max_sentences: int = 10) -> str:
    q_tokens = _question_tokens(question)
    ranked: list[tuple[float, int, str, str]] = []

    for idx, entry in enumerate(contexts, start=1):
        source, body = _split_context_entry(entry)
        body = re.sub(r"\s+", " ", body).strip()
        sentences = re.split(r"(?<=[\.!?;:])\s+", body)
        for sentence in sentences:
            clean = sentence.strip(" -\t\n")
            if len(clean) < 45:
                continue
            score = _sentence_score(clean, q_tokens)
            if not q_tokens:
                score += 0.15
            ranked.append((score, idx, source, clean))

    ranked.sort(key=lambda item: item[0], reverse=True)

    selected: list[str] = []
    used_sources: set[str] = set()
    seen_sentences: set[str] = set()
    for score, _, source, sentence in ranked:
        key = sentence.lower()
        if key in seen_sentences:
            continue
        if len(selected) >= max_sentences:
            break
        if source in used_sources and len(selected) >= max(4, max_sentences // 2) and score < 2.2:
            continue
        seen_sentences.add(key)
        used_sources.add(source)
        selected.append(f"- {sentence} ({source})")

    if not selected:
        fallback: list[str] = []
        for entry in contexts[:4]:
            source, body = _split_context_entry(entry)
            snippet = re.sub(r"\s+", " ", body).strip()[:260]
            if snippet:
                fallback.append(f"- {snippet}... ({source})")
        selected = fallback

    return "\n".join(selected)


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

    evidence_digest = _build_evidence_digest(question, contexts)

    llm = ChatOpenAI(
        model=_model(),
        base_url=_base_url(),
        api_key=_api_key(),
        temperature=float(os.getenv("IA_LOCAL_LLM_TEMPERATURE", "0.3")),
        top_p=float(os.getenv("IA_LOCAL_LLM_TOP_P", "0.85")),
        max_tokens=int(os.getenv("IA_LOCAL_LLM_MAX_TOKENS", "1200")),
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres MINDORA, asistente educativo offline de alto nivel especializado en explicaciones precisas, "
                "coherentes y de calidad profesional. Tu objetivo es replicar la consistencia y claridad de un chatbot "
                "educativo de primera categoría.\n\n"
                "PRINCIPIOS DE CALIDAD:\n"
                "• Coherencia: Cada respuesta fluye lógicamente de principio a fin sin contradicciones.\n"
                "• Profundidad: No superficial; explora causas, consecuencias, conexiones entre conceptos.\n"
                "• Precisión: Usa terminología exacta y referencias concretas del contexto.\n"
                "• Estructura: Intro clara → desarrollo → conclusión o aplicación.\n"
                "• Tono: Profesional, accesible, nunca patronizante.\n\n"
                "REGLAS DE CONTENIDO:\n"
                "1. CONTEXTO ES VERDAD: Usa ÚNICAMENTE información del contexto. Nunca inventes ni especules.\n"
                "2. EXPLICITACIÓN: Si falta información, dilo claramente sin excusas falsas.\n"
                "3. EJEMPLOS: Incluye ejemplos concretos del contexto para ilustrar conceptos.\n"
                "4. TRANSICIONES: Conecta ideas con frases transicionales (por lo tanto, de esta manera, esto implica).\n"
                "5. RIGOR: Distingue entre definiciones, procedimientos, teoría y práctica.\n"
                "6. CITAS: Referencia las fuentes del contexto de forma natural en el texto.\n"
                "7. EVITA REPETICIÓN: No repitas la misma idea con diferentes palabras.",
            ),
            (
                "human",
                "INSTRUCCIONES ESPECÍFICAS:\n"
                "Estilo solicitado: {style_rules}\n\n"
                "CONTEXTO PRINCIPAL:\n{context}\n\n"
                "EVIDENCIA CLAVE (prioriza esto):\n{evidence_digest}\n\n"
                "CONVERSACIÓN ANTERIOR (para continuidad):\n{history}\n\n"
                "PREGUNTA:\n{question}\n\n"
                "DIRECTIVAS DE EJECUCIÓN:\n"
                "1. Lee la pregunta y el historial para entender el contexto conversacional.\n"
                "2. Identifica la idea principal que debes comunicar basándote en el contexto.\n"
                "3. Estructura tu respuesta: apertura → cuerpo bien desarrollado → cierre.\n"
                "4. Asegúrate de que cada oración añade valor; evita relleno.\n"
                "5. Usa conectores lógicos (sin embargo, además, en consecuencia) para fluidez.\n"
                "6. Si citas fuentes, hazlo de forma orgánica: 'Como menciona [FUENTE], ...'.\n"
                "7. Al final, resume brevemente los puntos clave en 1-2 líneas."
            ),
        ]
    )

    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke(
        {
            "style_rules": _style_rules(response_style),
            "evidence_digest": evidence_digest,
            "context": "\n\n".join(contexts),
            "history": _history_text(history),
            "question": question,
        }
    )

    text = (answer or "").strip()
    if not text:
        return "No pude generar una respuesta en este momento con el modelo local."
    return text
