from __future__ import annotations

import os
import re
import threading
import sys
from pathlib import Path
from typing import Sequence, Literal

from llama_cpp import Llama
from app.services.intent_dictionary import detect_intent_and_style
from app.services.style_preferences import recommend_style
from app.storage.config import get_base_dir


_LLM_INSTANCE: Llama | None = None
_LLM_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Anti-robot postprocessing
# ---------------------------------------------------------------------------
_ROBOT_PATTERNS: list[re.Pattern] = [
    re.compile(r"como (?:se ha |hemos |ya |antes )mencionado(?: anteriormente)?,?\s*", re.I),
    re.compile(r"es (?:muy )?importante (?:destacar|mencionar|se\u00f1alar|recordar) que\s*", re.I),
    re.compile(r"en (?:conclusi\u00f3n|resumen),?\s+como (?:se puede|hemos|se ha) (?:ver|observar|visto),?\s*", re.I),
    re.compile(r"(?:sin duda(?:lguna)?|indudablemente|evidentemente),?\s*", re.I),
    re.compile(r"(?:cabe|es necesario|resulta importante) (?:destacar|mencionar|se\u00f1alar|recordar) que\s*", re.I),
    re.compile(r"a modo de (?:resumen|conclusi\u00f3n|cierre),?\s*", re.I),
    re.compile(r"(?:dicho esto|teniendo esto en cuenta|en este sentido),?\s*", re.I),
    re.compile(r"(?:tal y como|tal como) (?:hemos visto|se ha indicado|se puede ver),?\s*", re.I),
    re.compile(r"hay que (?:tener en cuenta|destacar|recordar) que\s*", re.I),
    re.compile(r"como (?:podemos|puedes) (?:ver|observar),?\s*", re.I),
    re.compile(r"es de destacar que\s*", re.I),
    re.compile(r"(?:finalmente|por \u00faltimo)[,.]?\s+cabe (?:decir|mencionar|a\u00f1adir)\s*", re.I),
]

# ---------------------------------------------------------------------------
# Few-shot style examples (short, embedded in prompts)
# ---------------------------------------------------------------------------
_FEW_SHOT_EXAMPLES: dict[str, str] = {
    "examen": (
        "Ejemplo de respuesta en MODO EXAMEN (imita este formato):\n"
        "1. Definici\u00f3n: La fotoS\u00edntesis es el proceso por el que las plantas convierten CO\u2082 y H\u2082O en glucosa mediante luz solar.\n"
        "2. Fases: Fase luminosa (cloroplastos, ATP) y Fase oscura (ciclo de Calvin, fijaci\u00f3n de CO\u2082).\n"
        "3. F\u00f3rmula: 6CO\u2082 + 6H\u2082O \u2192 C\u2086H\u2081\u2082O\u2086 + 6O\u2082\n"
        "Resumen: proceso an\u00e1bolo de producci\u00f3n de energ\u00eda en vegetales. [FUENTE 1]\n"
    ),
    "profesor": (
        "Ejemplo de respuesta en MODO PROFESOR (imita este formato):\n"
        "Introducci\u00f3n: Hoy vamos a entender qu\u00e9 es la fotoS\u00edntesis y por qu\u00e9 es fundamental.\n"
        "Desarrollo: Las plantas captan luz con la clorofila y la usan para transformar CO\u2082 y agua en glucosa.\n"
        "Ejemplo guiado: Una planta en una ventana soleada capta luz \u2192 produce az\u00facar \u2192 crece.\n"
        "Error frecuente: confundir fotoS\u00edntesis (fabrica glucosa) con respiraci\u00f3n celular (la consume).\n"
        "Pregunta de comprobaci\u00f3n: \u00bfQu\u00e9 pasar\u00eda si la planta no tuviera luz una semana?\n"
    ),
    "companero": (
        "Ejemplo de respuesta en MODO COMPA\u00d1ERO (imita este formato):\n"
        "Te lo explico f\u00e1cil: la fotoS\u00edntesis es c\u00f3mo las plantas se hacen su propia comida con luz solar.\n"
        "- Toman CO\u2082 del aire y agua del suelo.\n"
        "- Con la luz lo convierten en glucosa (su 'combustible').\n"
        "Regla r\u00e1pida: 'Luz + CO\u2082 + H\u2082O \u2192 az\u00facar + ox\u00edgeno'. \u00a1Simple!\n"
    ),
    "corta": (
        "Ejemplo de respuesta CORTA (imita este formato):\n"
        "La fotoS\u00edntesis convierte CO\u2082, H\u2082O y luz solar en glucosa y ox\u00edgeno en los cloroplastos. [FUENTE 1]\n"
    ),
}


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


def _lora_adapter_path() -> str | None:
    if os.getenv("IA_OFFLINE_DISABLE_LORA") is not None and _bool_env("IA_OFFLINE_DISABLE_LORA"):
        return None

    env_path = os.getenv("IA_OFFLINE_LORA_ADAPTER_PATH")
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists() and p.is_file():
            return str(p)

    ft_dir = get_base_dir() / "fine_tuning"
    candidates = [
        ft_dir / "llama_cpp_adapter.gguf",
        ft_dir / "lora_adapter.gguf",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)
    return None


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

        llama_kwargs: dict = {
            "model_path": path,
            "n_ctx": n_ctx,
            "n_threads": n_threads,
            "n_batch": n_batch,
            "verbose": False,
        }
        adapter = _lora_adapter_path()
        if adapter:
            llama_kwargs["lora_path"] = adapter

        try:
            _LLM_INSTANCE = Llama(**llama_kwargs)
        except TypeError:
            # Backward-compatible fallback for llama_cpp versions without lora_path.
            llama_kwargs.pop("lora_path", None)
            _LLM_INSTANCE = Llama(**llama_kwargs)
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


def _style_from_selector(style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"]) -> tuple[str, int] | None:
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
    if style == "examen":
        return (
            "1) Respuesta académica y precisa.\n"
            "2) Estructura en apartados numerados.\n"
            "3) Incluye términos clave del temario.\n"
            "4) Cierra con mini-resumen tipo examen.",
            650,
        )
    if style == "profesor":
        return (
            "1) Explica con claridad pedagógica.\n"
            "2) Introduce concepto, desarrollo y ejemplo guiado.\n"
            "3) Señala errores frecuentes del alumno.\n"
            "4) Cierra con una pregunta de comprobación.",
            700,
        )
    if style == "companero":
        return (
            "1) Tono cercano y natural.\n"
            "2) Explicación simple sin jerga innecesaria.\n"
            "3) Usa un ejemplo cotidiano breve.\n"
            "4) Cierra con una regla mnemotécnica corta.",
            520,
        )
    return None


def _remove_incomplete_tail(text: str) -> str:
    """Remove last sentence if it looks cut off (no ending punctuation)."""
    stripped = text.rstrip()
    if not stripped:
        return stripped
    if stripped[-1] not in ".!?\u2026\u00bb]":
        last_punct = max(stripped.rfind("."), stripped.rfind("!"), stripped.rfind("?"))
        if last_punct > len(stripped) // 2:
            return stripped[: last_punct + 1]
    return stripped


def _postprocess_answer(text: str, style: str) -> str:
    """Remove robotic filler, deduplicate, fix tail, enforce style constraints."""
    # 1. Strip robotic filler phrases
    for pattern in _ROBOT_PATTERNS:
        text = pattern.sub("", text)

    # 2. Collapse extra spaces created by removals
    text = re.sub(r"  +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 3. Deduplicate lines
    text = _dedupe_lines(text)

    # 4. Remove trailing incomplete sentence
    text = _remove_incomplete_tail(text)

    # 5. Style-specific constraints
    if style == "corta":
        lines = [ln for ln in text.splitlines() if ln.strip()]
        text = "\n".join(lines[:7])

    elif style == "companero":
        # If response starts very formally, soften opening
        if re.match(r"^(La |El |Se |Los |Las )", text):
            text = "Te lo cuento: " + text[0].lower() + text[1:]

    elif style == "examen":
        # Convert bullet list to numbered list for exam style
        if re.match(r"^[-\u2022]\s", text.lstrip()):
            lines = text.splitlines()
            converted: list[str] = []
            counter = 1
            for line in lines:
                stripped_line = line.strip()
                if re.match(r"^[-\u2022]\s", stripped_line):
                    converted.append(f"{counter}. " + stripped_line[2:].strip())
                    counter += 1
                else:
                    converted.append(line)
            text = "\n".join(converted)

    return text.strip()


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[\.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [p.strip() for p in parts if p.strip()]


def _strip_context_artifacts(text: str) -> str:
    cleaned = text or ""
    cleaned = re.sub(r"\[FUENTE\s+\d+\][^\n]*", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\[PAGE\s+\d+\]", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\[IMAGEN[^\]]*\]", " ", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip()


def _clean_extractive_text(text: str) -> str:
    text = re.sub(r"©\s*Copyright[^\.\n]*", "", text, flags=re.I)
    text = re.sub(r"\b\d{1,3}\s*/\s*\d{1,2}/\d{2,4}\b", "", text)
    text = re.sub(r"\b\d{2,4}\b(?=\s*$)", "", text)
    text = re.sub(r"[•·]+", ". ", text)
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return text


def _is_noisy_sentence(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True

    lower = s.lower()
    if any(
        marker in lower
        for marker in [
            "sin texto extraíble",
            "sin texto extraible",
            "tamaño",
            "px",
            "[imagen",
            "[page",
            "chunk",
        ]
    ):
        return True

    if len(s.split()) < 5:
        return True

    alpha = sum(1 for ch in s if ch.isalpha())
    digits = sum(1 for ch in s if ch.isdigit())
    if alpha < max(10, int(len(s) * 0.35)):
        return True
    if digits > int(len(s) * 0.22):
        return True

    upper_alpha = sum(1 for ch in s if ch.isalpha() and ch.isupper())
    if alpha > 0 and (upper_alpha / alpha) > 0.58 and len(s) > 45:
        return True

    return False


def _rank_sentences(question: str, sentences: list[str]) -> list[str]:
    q_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", question.lower()))
    scored: list[tuple[int, int, str]] = []
    for i, sentence in enumerate(sentences):
        cleaned = _clean_extractive_text(sentence)
        if len(cleaned) < 25:
            continue
        if _is_noisy_sentence(cleaned):
            continue
        s_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", cleaned.lower()))
        overlap = len(q_tokens.intersection(s_tokens))
        scored.append((overlap, -i, cleaned))
    scored.sort(reverse=True)
    ranked = [text for _, _, text in scored if text]
    fallback_clean = [
        _clean_extractive_text(s)
        for s in sentences
        if _clean_extractive_text(s) and not _is_noisy_sentence(_clean_extractive_text(s))
    ]
    return ranked or fallback_clean


def _extract_topic_from_question(question: str) -> str:
    q = (question or "").strip().lower()
    q = re.sub(r"[¿?]", "", q)
    q = re.sub(r"(?i)\bdel\s+pdf\b.*$", "", q).strip()
    patterns = [
        r"(?:qué|que)\s+es\s+(.+)",
        r"define\s+(.+)",
        r"definici[oó]n\s+de\s+(.+)",
        r"explica\s+(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, q, flags=re.I)
        if m:
            return m.group(1).strip(" .,:;-")
    return ""


def _best_definition_sentence(question: str, ranked: list[str]) -> str | None:
    topic = _extract_topic_from_question(question)
    topic_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", topic.lower())) if topic else set()

    for sentence in ranked:
        lower = sentence.lower()
        if not any(k in lower for k in [" es ", " se define", " consiste en", " es el", " es la"]):
            continue
        if not topic_tokens:
            return sentence
        s_tokens = set(re.findall(r"[a-záéíóúñ0-9]{4,}", lower))
        if len(topic_tokens.intersection(s_tokens)) >= 1:
            return sentence
    return None


def generate_answer_fallback(
    question: str,
    contexts: list[str],
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"] = "auto",
) -> str:
    """Deterministic extractive fallback used when local LLM is unstable/unavailable."""
    if not contexts:
        return "No encontré información suficiente en el contexto para responder."

    clean_contexts = [_strip_context_artifacts(c) for c in contexts[:4] if c and c.strip()]
    merged = "\n\n".join(clean_contexts)
    sentences = _split_sentences(merged)
    if not sentences:
        return contexts[0][:700]
    ranked = _rank_sentences(question, sentences)
    if not ranked:
        return (
            "No encontré fragmentos suficientemente claros del documento para responder con precisión. "
            "Prueba con una pregunta más concreta (por ejemplo: '¿Qué es el riesgo residual según el PDF?')."
        )

    q = question.lower()
    wants_steps = response_style in {"pasos", "detallada_pasos"} or "paso a paso" in q or "fácil" in q
    wants_short = response_style == "corta" or "1 minuto" in q or "resumen" in q

    if wants_short:
        selected = ranked[:3]
        result = "\n".join(f"- {s}" for s in selected)
        return _postprocess_answer(result, "corta")

    if wants_steps:
        selected = ranked[:4]
        result = "\n".join(f"{i + 1}) {s}" for i, s in enumerate(selected))
        return _postprocess_answer(result, response_style)

    if response_style == "examen":
        selected = ranked[:4]
        result = (
            "\n".join(f"{i + 1}. {s}" for i, s in enumerate(selected))
            + "\n\nConclusión: idea central del tema y aplicación directa."
        )
        return _postprocess_answer(result, "examen")

    if response_style == "profesor":
        selected = ranked[:4]
        definition = _best_definition_sentence(question, ranked)
        intro = definition or (selected[0] if selected else "")
        bullets = [s for s in selected if s != intro][:2]
        example = next((s for s in ranked if re.search(r"\b(ejemplo|por ejemplo|caso)\b", s, flags=re.I)), "")
        if not example and len(selected) > 2:
            example = selected[2]
        result = "\n".join(
            [
                "Definición breve:",
                intro,
                "",
                "Puntos clave:",
                "- " + "\n- ".join(bullets) if bullets else "",
                "",
                "Ejemplo guiado:",
                example,
                "",
                "Para comprobar que lo entendiste:",
                "¿Cómo lo explicarías tú en una frase con tus propias palabras?",
            ]
        ).strip()
        return _postprocess_answer(result, "profesor")

    if response_style == "companero":
        selected = ranked[:3]
        result = "Te lo explico f\u00e1cil:\n- " + "\n- ".join(selected)
        return _postprocess_answer(result, response_style)

    selected = ranked[:5]
    result = "\n".join(selected)
    return _postprocess_answer(result, response_style)


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
    response_style: Literal["auto", "corta", "detallada", "pasos", "detallada_pasos", "examen", "profesor", "companero"] = "auto",
    history: list[dict] | None = None,
) -> str:
    if _should_use_safe_mode():
        return generate_answer_fallback(question, contexts, response_style)

    detected_intent, detected_style = detect_intent_and_style(question)
    preferred_style = recommend_style(question)
    if response_style != "auto":
        effective_style = response_style
    elif preferred_style:
        effective_style = preferred_style
    else:
        effective_style = detected_style

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

    few_shot = _FEW_SHOT_EXAMPLES.get(effective_style, "")
    few_shot_block = f"\n{few_shot}\n" if few_shot else ""

    prompt = (
        "Eres MINDORA, una IA educativa offline experta en explicar temarios.\n"
        "Reglas estrictas:\n"
        "- Responde SOLO con la informaci\u00f3n del contexto recuperado.\n"
        "- No inventes datos, leyes, fechas o definiciones.\n"
        "- Si falta informaci\u00f3n, dilo expl\u00edcitamente.\n"
        "- Escribe en espa\u00f1ol claro, estructurado y natural.\n"
        "- Incluye al menos un ejemplo pr\u00e1ctico cuando sea posible.\n"
        "- Evita frases rob\u00f3ticas y repetitivas; escribe como una persona.\n"
        "- Cita al final las fuentes usadas usando etiquetas [FUENTE n] del contexto.\n"
        f"Intenci\u00f3n detectada del usuario: {detected_intent}.\n"
        f"Formato de respuesta:\n{style_rules}\n"
        f"{few_shot_block}\n"
        f"Contexto:\n{context_block}\n\n"
        f"{history_block}\n\n"
        f"Pregunta: {question}\n"
        "Respuesta:"
    )
    raw = generate_text(prompt, max_tokens=max_tokens, temperature=0.15, stop=["\n\nPregunta:"])
    cleaned = _dedupe_lines(raw)
    return _postprocess_answer(cleaned, effective_style)
