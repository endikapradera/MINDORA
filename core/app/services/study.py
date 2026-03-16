from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from app.services.llm import generate_text
from app.services.query import retrieve_chunks
from app.storage.branches import get_branch_path, branch_exists


def _extract_list_items(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip bullet markers: "- ", "* ", "• ", numbered "1. ", "1) ", etc.
        line = re.sub(r"^(\d+[.\)]\s*|[-*•]\s*)", "", line).strip()
        if line:
            items.append(line)
    return items[:12]


def _extract_section(full_text: str, section_name: str) -> str:
    pattern = re.compile(rf"(?ims)^##\s*{re.escape(section_name)}\s*$")
    matches = list(pattern.finditer(full_text))
    if not matches:
        return ""
    start = matches[0].end()
    next_headers = re.finditer(r"(?im)^##\s+", full_text[start:])
    next_header = next(next_headers, None)
    end = start + next_header.start() if next_header else len(full_text)
    return full_text[start:end].strip()


def generate_study_pack(branch: str, topic: str, top_k: int = 6) -> dict:
    chunks = retrieve_chunks(branch, topic, top_k=top_k)
    if not chunks:
        raise RuntimeError("No hay contexto suficiente para generar el pack de estudio.")

    context_block = "\n\n".join(c["text"] for c in chunks)[:3800]
    sources = [f"{c.get('filename', 'documento')} (chunk {c.get('chunk_index', 0)})" for c in chunks]

    prompt = (
        "Genera un pack de estudio en español basado SOLO en el contexto.\n"
        "Devuelve EXACTAMENTE estas secciones con encabezado '##':\n"
        "## RESUMEN_CORTO\n"
        "## RESUMEN_LARGO\n"
        "## IDEAS_CLAVE\n"
        "## CONCEPTOS_MEMORIZAR\n"
        "## POSIBLES_PREGUNTAS_EXAMEN\n"
        "## ERRORES_TIPICOS\n"
        "## MINI_TEST_5\n"
        "En IDEAS_CLAVE, CONCEPTOS_MEMORIZAR, POSIBLES_PREGUNTAS_EXAMEN, ERRORES_TIPICOS y MINI_TEST_5 usa listas con viñetas.\n"
        "Sin texto adicional fuera de esas secciones.\n\n"
        f"Tema: {topic}\n"
        f"Contexto:\n{context_block}\n"
    )

    raw = generate_text(prompt, max_tokens=1000, temperature=0.15)

    summary_short = _extract_section(raw, "RESUMEN_CORTO")
    summary_long = _extract_section(raw, "RESUMEN_LARGO")
    key_ideas = _extract_list_items(_extract_section(raw, "IDEAS_CLAVE"))
    concepts_to_memorize = _extract_list_items(_extract_section(raw, "CONCEPTOS_MEMORIZAR"))
    possible_exam_questions = _extract_list_items(_extract_section(raw, "POSIBLES_PREGUNTAS_EXAMEN"))
    common_mistakes = _extract_list_items(_extract_section(raw, "ERRORES_TIPICOS"))
    mini_test = _extract_list_items(_extract_section(raw, "MINI_TEST_5"))

    if len(mini_test) < 3:
        mini_prompt = (
            "Genera 5 mini preguntas rápidas de repaso sobre el tema, en formato lista. "
            "Combina verdadero/falso, test corto y una pregunta breve de desarrollo.\n"
            f"Tema: {topic}\n"
            f"Contexto:\n{context_block}\n"
        )
        mini_raw = generate_text(mini_prompt, max_tokens=260, temperature=0.15)
        mini_test = _extract_list_items(mini_raw)

    if not summary_short:
        summary_short = "Resumen no disponible con suficiente calidad."
    if not summary_long:
        summary_long = "Resumen ampliado no disponible con suficiente calidad."

    return {
        "topic": topic,
        "summary_short": summary_short,
        "summary_long": summary_long,
        "key_ideas": key_ideas,
        "concepts_to_memorize": concepts_to_memorize,
        "possible_exam_questions": possible_exam_questions,
        "common_mistakes": common_mistakes,
        "mini_test": mini_test,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# Daily recommendations (spaced repetition from simulation history)
# ---------------------------------------------------------------------------

def get_daily_recommendations(branch: str, max_recommendations: int = 5) -> dict:
    """
    Aggregate weak_topics from all completed simulations and return
    a prioritised list of topics to study today, ordered by fail frequency.
    """
    if not branch_exists(branch):
        raise FileNotFoundError()

    sim_dir = get_branch_path(branch) / "Exams" / "simulations"
    if not sim_dir.exists():
        return {"recommendations": [], "message": "Aún no hay simulacros completados."}

    topic_fail_count: Counter = Counter()
    topic_last_seen: dict[str, str] = {}
    completed = 0

    for path in sim_dir.glob("simulation_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if data.get("status") not in ("submitted", "timed_out"):
            continue
        completed += 1

        submitted_at = data.get("submitted_at") or ""
        for wt in data.get("answers", []):
            pass  # answers don't carry weak_topics

        # Re-derive weak topics from results stored inside answers
        # (weak_topics is not persisted in simulation JSON directly –
        #  we need to compute from per-question results if present)
        # Fallback: use topic as a single weak item if score < 50
        score = data.get("score_percent")
        topic = data.get("topic", "")
        if score is not None and float(score) < 50 and topic:
            topic_fail_count[topic] += 1
            if submitted_at > topic_last_seen.get(topic, ""):
                topic_last_seen[topic] = submitted_at

    if completed == 0:
        return {"recommendations": [], "message": "Aún no hay simulacros completados."}

    if not topic_fail_count:
        return {
            "recommendations": [],
            "message": "¡Excelente! Has superado el 50% en todos los simulacros.",
        }

    sorted_topics = topic_fail_count.most_common(max_recommendations)
    recommendations = [
        {
            "topic": topic,
            "fail_count": count,
            "last_failed": topic_last_seen.get(topic, ""),
            "suggestion": f"Repasa '{topic}' – has fallado {count} vez{'es' if count > 1 else ''}. "
                          f"Genera un pack de estudio o un simulacro nuevo sobre este tema.",
        }
        for topic, count in sorted_topics
    ]

    return {
        "recommendations": recommendations,
        "message": f"Basado en {completed} simulacro{'s' if completed != 1 else ''} completado{'s' if completed != 1 else ''}.",
    }
