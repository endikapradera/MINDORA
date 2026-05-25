"""
exam_validator.py — Fase 4: Validación de distractores y scoring de confianza.

Para cada pregunta tipo test generada:
  1. Verificar que la respuesta correcta está respaldada por el contexto.
  2. Verificar que cada distractor (opción incorrecta) es realmente falso.
  3. Calcular un score de confianza [0.0–1.0] por pregunta.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Minimum lexical overlap ratio to consider an answer "grounded" in context
_GROUNDING_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúñ0-9]{4,}", text.lower()))


def _grounding_score(text: str, context_tokens: set[str]) -> float:
    """Ratio of text tokens that appear in the context vocabulary."""
    t = _tokens(text)
    if not t:
        return 0.0
    overlap = len(t & context_tokens)
    return overlap / len(t)


def _is_grounded(text: str, context_tokens: set[str]) -> bool:
    return _grounding_score(text, context_tokens) >= _GROUNDING_THRESHOLD


def _option_letter(option_str: str) -> str:
    """Extract letter from 'A) ...' → 'A'."""
    m = re.match(r"^([A-D])\s*[\).]", option_str.strip())
    return m.group(1) if m else ""


def _option_text(option_str: str) -> str:
    """Extract body text from 'A) Texto' → 'Texto'."""
    return re.sub(r"^[A-D]\s*[\).]\s*", "", option_str.strip())


def _correct_letters(answer: str) -> set[str]:
    return set(re.findall(r"\b([A-D])\b", answer.upper()))


# ---------------------------------------------------------------------------
# LLM-based distractor check (optional, graceful fallback)
# ---------------------------------------------------------------------------

def _llm_verify_distractor(
    statement: str,
    distractor_text: str,
    context_block: str,
) -> tuple[bool, str]:
    """
    Ask the LLM whether the distractor is clearly false given the context.
    Returns (is_clearly_false, reason).
    Falls back to True (assume valid) on any error.
    """
    try:
        from app.services.llm import generate_text  # lazy import to avoid circular
    except Exception:
        return True, "LLM no disponible"

    prompt = (
        "Eres un corrector académico. Dado el contexto del temario, determina si la afirmación es FALSA.\n"
        "Contexto:\n" + context_block[:1200] + "\n\n"
        f"Pregunta: {statement}\n"
        f"Afirmación a verificar: {distractor_text}\n\n"
        "Responde SOLO con:\n"
        "VEREDICTO: FALSO o VERDADERO\n"
        "RAZÓN: <una frase muy corta>\n"
    )
    try:
        raw = generate_text(prompt, max_tokens=60, temperature=0.0)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        verdict = ""
        reason = ""
        for line in lines:
            low = line.lower()
            if low.startswith("veredicto:"):
                verdict = line.split(":", 1)[1].strip().upper()
            elif low.startswith("razón:") or low.startswith("razon:"):
                reason = line.split(":", 1)[1].strip()
        is_false = "FALSO" in verdict
        return is_false, reason or ("Distractor válido" if is_false else "Podría ser verdadero")
    except Exception as exc:
        logger.debug("Distractor LLM check failed: %s", exc)
        return True, "Verificación no disponible"


def _llm_verify_correct_answer(
    statement: str,
    answer_text: str,
    context_block: str,
) -> tuple[bool, float]:
    """
    Ask the LLM whether the correct answer is supported by the context.
    Returns (is_supported, confidence_boost).
    Falls back gracefully.
    """
    try:
        from app.services.llm import generate_text
    except Exception:
        return True, 0.0

    prompt = (
        "Eres un corrector académico. Dado el contexto del temario, determina si la respuesta es CORRECTA.\n"
        "Contexto:\n" + context_block[:1200] + "\n\n"
        f"Pregunta: {statement}\n"
        f"Respuesta propuesta: {answer_text}\n\n"
        "Responde SOLO con:\n"
        "VEREDICTO: CORRECTA o INCORRECTA\n"
        "RAZÓN: <una frase muy corta>\n"
    )
    try:
        raw = generate_text(prompt, max_tokens=60, temperature=0.0)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        for line in lines:
            if line.lower().startswith("veredicto:"):
                v = line.split(":", 1)[1].strip().upper()
                return "CORRECTA" in v, 0.15 if "CORRECTA" in v else -0.15
        return True, 0.0
    except Exception:
        return True, 0.0


# ---------------------------------------------------------------------------
# Per-question validation
# ---------------------------------------------------------------------------

def validate_question(
    question: dict,
    context_texts: list[str],
    use_llm: bool = False,
) -> dict:
    """
    Validate a single question dict.

    Returns the question dict enriched with:
      - confidence: float [0.0–1.0]
      - distractor_issues: list[str]  (warnings about potentially true distractors)
      - answer_grounded: bool
    """
    context_block = "\n\n".join(context_texts[:4])
    ctx_tokens = _tokens(context_block)

    q_type = question.get("type", "test")
    statement = question.get("statement", "")
    answer = question.get("answer", "")
    options: list[str] = question.get("options", [])

    distractor_issues: list[str] = []
    confidence = 1.0

    if q_type == "test":
        correct_set = _correct_letters(answer)

        # 1. Check correct answer is grounded
        correct_option_texts: list[str] = []
        for opt in options:
            letter = _option_letter(opt)
            text = _option_text(opt)
            if letter in correct_set:
                correct_option_texts.append(text)

        answer_text_combined = " ".join(correct_option_texts) or answer
        answer_grounded = _is_grounded(answer_text_combined, ctx_tokens)

        if not answer_grounded:
            confidence -= 0.25
            logger.debug("Q%s: correct answer not grounded in context", question.get("number"))

        # Optional LLM boost/penalty on answer
        if use_llm and options:
            _, boost = _llm_verify_correct_answer(statement, answer_text_combined, context_block)
            confidence = min(1.0, max(0.0, confidence + boost))

        # 2. Verify distractors
        for opt in options:
            letter = _option_letter(opt)
            text = _option_text(opt)
            if not text or letter in correct_set:
                continue  # skip correct options

            # Lexical check: if distractor is too similar to context AND too similar to answer → suspicious
            grounding = _grounding_score(text, ctx_tokens)
            answer_similarity = len(_tokens(text) & _tokens(answer_text_combined)) / max(1, len(_tokens(text)))

            if grounding > 0.70 and answer_similarity < 0.3:
                # Distractor heavily uses context vocab but differs from answer — could be true
                if use_llm:
                    is_false, reason = _llm_verify_distractor(statement, text, context_block)
                    if not is_false:
                        issue = f"Opción {letter}: '{text[:60]}' podría ser verdadera ({reason})"
                        distractor_issues.append(issue)
                        confidence -= 0.20
                else:
                    # Conservative: flag but don't penalise heavily without LLM confirmation
                    issue = f"Opción {letter}: revisar si '{text[:60]}' es realmente falsa"
                    distractor_issues.append(issue)
                    confidence -= 0.10

        answer_grounded_flag = answer_grounded

    else:
        # Development question: confidence based on answer grounding
        answer_grounded_flag = _is_grounded(answer, ctx_tokens)
        if not answer_grounded_flag:
            confidence -= 0.30

        if use_llm:
            _, boost = _llm_verify_correct_answer(statement, answer, context_block)
            confidence = min(1.0, max(0.0, confidence + boost))

    confidence = round(max(0.0, min(1.0, confidence)), 2)

    return {
        **question,
        "confidence": confidence,
        "distractor_issues": distractor_issues,
        "answer_grounded": answer_grounded_flag,
    }


def validate_exam_questions(
    questions: list[dict],
    context_texts: list[str],
    use_llm: bool = False,
) -> list[dict]:
    """
    Validate all questions in an exam. Returns enriched question list.
    Questions with confidence < 0.4 are flagged (not removed).
    """
    validated: list[dict] = []
    for q in questions:
        try:
            vq = validate_question(q, context_texts, use_llm=use_llm)
        except Exception as exc:  # pragma: no cover
            logger.warning("Validation failed for question %s: %s", q.get("number"), exc)
            vq = {**q, "confidence": 0.5, "distractor_issues": [], "answer_grounded": True}
        validated.append(vq)

    # Log summary
    avg_conf = sum(v["confidence"] for v in validated) / max(1, len(validated))
    low_conf = [v["number"] for v in validated if v["confidence"] < 0.5]
    logger.info(
        "Exam validation: %d questions, avg confidence=%.2f, low-confidence=%s",
        len(validated),
        avg_conf,
        low_conf,
    )
    return validated


# ---------------------------------------------------------------------------
# Confidence scoring for solved uploaded exams
# ---------------------------------------------------------------------------

def score_solved_answer(answer_text: str, context_texts: list[str]) -> float:
    """
    Return a confidence score [0.0–1.0] for a single solved answer.
    Based on:
    - Lexical grounding in context
    - Presence of "no sé" / "no hay información" type phrases (→ low confidence)
    """
    low_conf_phrases = [
        "no tengo información",
        "no encontré",
        "falta información",
        "no se menciona",
        "no puedo responder",
        "no hay datos",
        "no está en el contexto",
    ]
    text_lower = answer_text.lower()
    if any(phrase in text_lower for phrase in low_conf_phrases):
        return 0.15

    ctx_tokens = _tokens("\n".join(context_texts[:4]))
    grounding = _grounding_score(answer_text, ctx_tokens)

    # Map grounding to confidence with a mild curve
    if grounding >= 0.5:
        return 1.0
    if grounding >= 0.35:
        return 0.80
    if grounding >= 0.20:
        return 0.60
    if grounding >= 0.10:
        return 0.40
    return 0.25
