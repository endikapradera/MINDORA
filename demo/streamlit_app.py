from __future__ import annotations

import re
import uuid
import requests
import streamlit as st

BASE_URL = st.secrets.get("MINDORA_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="MINDORA · Demo Práctica 2", page_icon="📚", layout="wide")
st.title("📚 MINDORA · Demo Práctica 2 (Offline)")
st.caption("LangChain + Ollama/LM Studio + FastAPI (modo local)")

# ── Session state defaults ─────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:10]}"
if "chat" not in st.session_state:
    st.session_state.chat = []
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = []
if "exam_index" not in st.session_state:
    st.session_state.exam_index = 0
if "exam_answers" not in st.session_state:
    st.session_state.exam_answers = {}
if "exam_revealed" not in st.session_state:
    st.session_state.exam_revealed = {}
if "exam_topic" not in st.session_state:
    st.session_state.exam_topic = ""


# ── API helpers ────────────────────────────────────────────────────────────
def api_get(path: str, **params):
    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=40)
    resp.raise_for_status()
    return resp.json()


def api_post(path: str, *, json=None, params=None, files=None, data=None):
    resp = requests.post(
        f"{BASE_URL}{path}",
        json=json,
        params=params,
        files=files,
        data=data,
        timeout=240,
    )
    resp.raise_for_status()
    return resp.json()


# ── Sidebar: branch & documents ───────────────────────────────────────────
with st.sidebar:
    st.header("Rama y documentos")

    try:
        branches = api_get("/api/branches")
    except Exception as exc:
        st.error(f"No se pudo conectar al backend: {exc}")
        st.stop()

    branch_names = [b["name"] for b in branches] if branches else []
    selected_branch = st.selectbox("Rama activa", branch_names, index=0 if branch_names else None)

    new_branch = st.text_input("Nueva rama")
    if st.button("Crear rama", use_container_width=True) and new_branch.strip():
        try:
            api_post("/api/branches", json={"name": new_branch.strip()})
            st.success("Rama creada")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    uploaded = st.file_uploader(
        "Subir documento",
        type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "csv", "txt", "md", "docx", "pptx"],
    )
    if st.button("Ingerir documento", use_container_width=True, disabled=not (selected_branch and uploaded)):
        try:
            payload = api_post(
                "/api/documents/ingest",
                files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/octet-stream")},
                data={"branch": selected_branch},
            )
            st.success(f"Ingerido (chunks: {payload.get('chunks', 0)})")
        except Exception as exc:
            st.error(f"Error en ingesta: {exc}")

    st.divider()
    st.subheader("Escenarios demo")
    if st.button("Escenario 1 - Resumen PDF", use_container_width=True):
        st.session_state.prefill = "Resumeme este documento en 5 puntos clave y termina con una conclusion breve."
    if st.button("Escenario 2 - Imagen/OCR", use_container_width=True):
        st.session_state.prefill = "Extrae la informacion principal de la imagen y explicamela de forma sencilla."
    if st.button("Escenario 3 - CSV", use_container_width=True):
        st.session_state.prefill = "Analiza el CSV, identifica tendencias y dame recomendaciones accionables."


# ── Main area: two tabs ────────────────────────────────────────────────────
tab_chat, tab_exam = st.tabs(["Chat contextual", "Examen interactivo A-B-C-D"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    question = st.text_area(
        "Pregunta",
        value=st.session_state.get("prefill", ""),
        height=90,
        placeholder="Escribe una pregunta sobre el documento cargado...",
    )
    style = st.selectbox(
        "Estilo de respuesta",
        ["auto", "corta", "detallada", "pasos", "examen", "profesor", "companero"],
        index=0,
    )

    col_a, col_b = st.columns(2)
    send = col_a.button("Enviar", use_container_width=True, disabled=not (selected_branch and question.strip()))
    clear = col_b.button("Limpiar chat", use_container_width=True)

    if clear:
        st.session_state.chat = []

    if send:
        try:
            payload = api_post(
                "/api/ask",
                params={"branch": selected_branch},
                json={
                    "question": question.strip(),
                    "top_k": 8,
                    "response_style": style,
                    "session_id": st.session_state.session_id,
                    "document_id": None,
                },
            )
            st.session_state.chat.append(("user", question.strip()))
            st.session_state.chat.append(("assistant", payload.get("answer", "")))
            st.session_state.last_sources = payload.get("sources", [])
        except Exception as exc:
            st.error(f"Error consultando IA: {exc}")

    st.markdown("---")
    for role, msg in st.session_state.chat:
        if role == "user":
            st.markdown(f"**Tu:** {msg}")
        else:
            st.markdown(f"**MINDORA:**\n\n{msg}")

    if st.session_state.get("last_sources"):
        st.markdown("---")
        st.markdown("**Fuentes del contexto:**")
        for src in st.session_state["last_sources"]:
            st.write(f"- {src}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: EXAMEN INTERACTIVO A-B-C-D
# ══════════════════════════════════════════════════════════════════════════════
with tab_exam:
    st.markdown("### Examen tipo test (A / B / C / D)")
    st.caption("El sistema genera preguntas con 4 opciones. Responde y descubre al instante si acertaste.")

    # ── Generar nuevo examen ───────────────────────────────────────────────
    with st.expander("Configurar y generar examen", expanded=not st.session_state.exam_questions):
        exam_topic = st.text_input("Tema del examen", placeholder="Ej: Redes neuronales, Historia de Roma...")
        exam_n = st.slider("Numero de preguntas", min_value=3, max_value=20, value=5)
        exam_diff = st.selectbox("Dificultad", ["facil", "media", "dificil"], index=1)
        exam_topk = st.number_input("Top-K contexto", min_value=3, max_value=15, value=6)

        gen_disabled = not (selected_branch and exam_topic.strip())
        if st.button("Generar examen", use_container_width=True, disabled=gen_disabled):
            with st.spinner("Generando preguntas..."):
                try:
                    result = api_post(
                        "/api/exams/generate",
                        params={"branch": selected_branch},
                        json={
                            "topic": exam_topic.strip(),
                            "num_questions": exam_n,
                            "difficulty": exam_diff,
                            "top_k": exam_topk,
                            "exam_type": "test",
                        },
                    )
                    exam_id = result.get("exam_id", "")
                    sim = api_post(
                        "/api/exams/simulation/start",
                        params={"branch": selected_branch},
                        json={"exam_id": exam_id, "duration_minutes": 120},
                    )
                    qs = sim.get("questions", [])

                    # Parse answer key
                    answer_key = result.get("answer_key_content", "")
                    answer_map = {}
                    explanation_map = {}
                    last_n = None
                    for line in answer_key.splitlines():
                        m = re.match(r"(\d+)\)\s*Respuesta:\s*(.+)", line.strip())
                        if m:
                            last_n = int(m.group(1))
                            answer_map[last_n] = m.group(2).strip()
                        m2 = re.match(r"\s*Justificaci.n:\s*(.+)", line.strip())
                        if m2 and last_n:
                            explanation_map[last_n] = m2.group(1).strip()

                    for q in qs:
                        n = int(q.get("number", 0))
                        q["answer"] = answer_map.get(n, "?")
                        q["explanation"] = explanation_map.get(n, "")

                    st.session_state.exam_questions = qs
                    st.session_state.exam_index = 0
                    st.session_state.exam_answers = {}
                    st.session_state.exam_revealed = {}
                    st.session_state.exam_topic = exam_topic.strip()
                    st.success(f"Examen generado: {len(qs)} preguntas sobre '{exam_topic.strip()}'")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Error generando examen: {exc}")

    # ── Mostrar examen pregunta a pregunta ─────────────────────────────────
    questions = st.session_state.exam_questions
    if not questions:
        st.info("Configura un tema y genera el examen para empezar.")
        st.stop()

    total = len(questions)
    answered = len(st.session_state.exam_revealed)
    correct_so_far = 0
    for n, letter in st.session_state.exam_answers.items():
        if n in st.session_state.exam_revealed:
            expected = next((q["answer"] for q in questions if q["number"] == n), "?")
            if letter.upper().strip(".)") == expected.upper().strip(".)"):
                correct_so_far += 1

    # Progress
    st.markdown(f"**{st.session_state.exam_topic}** - {answered}/{total} respondidas - Correctas: {correct_so_far}")
    st.progress(answered / total if total else 0)

    # Current question
    idx = st.session_state.exam_index
    idx = max(0, min(idx, total - 1))
    q = questions[idx]
    q_num = int(q.get("number", idx + 1))
    statement = q.get("statement", "")
    options = q.get("options", [])
    correct_answer = q.get("answer", "?").upper().strip(".)")
    explanation = q.get("explanation", "")

    # Build option map {A: text, B: text, ...}
    opt_map = {}
    for opt in options:
        m = re.match(r"([A-D])\s*[).]\s*(.*)", opt.strip())
        if m:
            opt_map[m.group(1).upper()] = m.group(2).strip()
    if not opt_map:
        for i, opt in enumerate(options):
            letter = "ABCD"[i] if i < 4 else str(i)
            opt_map[letter] = opt

    st.markdown("---")
    st.markdown(f"#### Pregunta {q_num} de {total}")
    st.markdown(f"**{statement}**")
    st.markdown("")

    already_revealed = q_num in st.session_state.exam_revealed
    chosen = st.session_state.exam_answers.get(q_num, None)

    if not already_revealed:
        option_labels = [f"{k}) {v}" for k, v in sorted(opt_map.items())]
        selection = st.radio(
            "Elige tu respuesta:",
            options=option_labels,
            key=f"radio_q{q_num}",
            index=None,
        )
        if st.button("Confirmar respuesta", disabled=selection is None, use_container_width=True):
            chosen_letter = selection[0].upper() if selection else ""
            st.session_state.exam_answers[q_num] = chosen_letter
            st.session_state.exam_revealed[q_num] = True
            st.rerun()
    else:
        # Show result
        for letter, text in sorted(opt_map.items()):
            is_correct_opt = letter == correct_answer
            is_chosen_opt = letter == (chosen or "").upper().strip(".)")
            if is_correct_opt:
                st.success(f"**{letter}) {text}**  <- Respuesta correcta")
            elif is_chosen_opt and not is_correct_opt:
                st.error(f"**{letter}) {text}**  <- Tu respuesta (incorrecta)")
            else:
                st.write(f"{letter}) {text}")

        if chosen and chosen.upper().strip(".)") == correct_answer:
            st.balloons()
            st.markdown("### Correcto!")
        else:
            st.markdown(f"### Incorrecto. La respuesta correcta era **{correct_answer}**")

        if explanation:
            st.info(f"Explicacion: {explanation}")

    # Navigation
    st.markdown("---")
    nav_prev, nav_next = st.columns(2)
    if nav_prev.button("Anterior", disabled=idx == 0, use_container_width=True):
        st.session_state.exam_index = idx - 1
        st.rerun()
    if nav_next.button("Siguiente", disabled=idx == total - 1, use_container_width=True):
        st.session_state.exam_index = idx + 1
        st.rerun()

    # Final score
    if answered == total:
        st.markdown("---")
        score_pct = round(correct_so_far / total * 100, 1)
        st.markdown(f"## Resultado final: {correct_so_far}/{total} ({score_pct}%)")
        if score_pct >= 80:
            st.success("Excelente! Dominas el tema.")
        elif score_pct >= 50:
            st.warning("Bien, pero repasa algunos conceptos.")
        else:
            st.error("Sigue estudiando. Revisa el material e intentalo de nuevo.")

        if st.button("Nuevo examen", use_container_width=True):
            st.session_state.exam_questions = []
            st.session_state.exam_index = 0
            st.session_state.exam_answers = {}
            st.session_state.exam_revealed = {}
            st.rerun()
