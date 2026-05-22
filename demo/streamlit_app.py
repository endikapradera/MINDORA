from __future__ import annotations

import uuid
import requests
import streamlit as st

BASE_URL = st.secrets.get("MINDORA_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="MINDORA · Demo Práctica 2", page_icon="📚", layout="wide")
st.title("📚 MINDORA · Demo Práctica 2 (Offline)")
st.caption("LangChain + Ollama/LM Studio + FastAPI (modo local)")


if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit-{uuid.uuid4().hex[:10]}"
if "chat" not in st.session_state:
    st.session_state.chat = []


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


left, right = st.columns([1, 2])

with left:
    st.subheader("1) Rama y documentos")

    try:
        branches = api_get("/api/branches")
    except Exception as exc:
        st.error(f"No se pudo conectar al backend: {exc}")
        st.stop()

    branch_names = [b["name"] for b in branches] if branches else []
    selected_branch = st.selectbox("Rama", branch_names, index=0 if branch_names else None)

    new_branch = st.text_input("Nueva rama")
    if st.button("Crear rama", use_container_width=True) and new_branch.strip():
        try:
            api_post("/api/branches", json={"name": new_branch.strip()})
            st.success("Rama creada")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

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
            st.success(f"Documento ingerido (chunks: {payload.get('chunks', 0)})")
        except Exception as exc:
            st.error(f"Error en ingesta: {exc}")

    st.divider()
    st.subheader("2) Escenarios demo")

    if st.button("Escenario 1 · Resumen PDF", use_container_width=True):
        st.session_state.prefill = "Resúmeme este documento en 5 puntos clave y termina con una conclusión breve."
    if st.button("Escenario 2 · Imagen/OCR", use_container_width=True):
        st.session_state.prefill = "Extrae la información principal de la imagen y explícamela de forma sencilla."
    if st.button("Escenario 3 · CSV", use_container_width=True):
        st.session_state.prefill = "Analiza el CSV, identifica tendencias y dame recomendaciones accionables."

with right:
    st.subheader("3) Chat contextual")

    question = st.text_area(
        "Pregunta",
        value=st.session_state.get("prefill", ""),
        height=90,
        placeholder="Escribe una pregunta sobre el documento cargado...",
    )
    style = st.selectbox(
        "Estilo",
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
            st.markdown(f"**🧑 Tú:** {msg}")
        else:
            st.markdown(f"**🤖 MINDORA:**\n\n{msg}")

    if st.session_state.get("last_sources"):
        st.markdown("---")
        st.markdown("**Fuentes del contexto:**")
        for src in st.session_state["last_sources"]:
            st.write(f"- {src}")
