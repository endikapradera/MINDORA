from __future__ import annotations

import os
from functools import lru_cache

from llama_cpp import Llama


def _model_path() -> str:
    path = os.getenv("IA_OFFLINE_LLM_PATH")
    if not path:
        raise RuntimeError("LLM model path not configured. Set IA_OFFLINE_LLM_PATH.")
    return path


@lru_cache(maxsize=1)
def get_llm() -> Llama:
    path = _model_path()
    n_ctx = int(os.getenv("IA_OFFLINE_LLM_CTX", "2048"))
    n_threads = int(os.getenv("IA_OFFLINE_LLM_THREADS", "4"))
    return Llama(model_path=path, n_ctx=n_ctx, n_threads=n_threads)


def build_prompt(question: str, contexts: list[str]) -> str:
    context_block = "\n\n".join(contexts)
    return (
        "Eres una IA educativa offline. Responde SOLO con la información dada. "
        "Si no está en el contexto, di que no hay información suficiente.\n\n"
        f"Contexto:\n{context_block}\n\n"
        f"Pregunta: {question}\n"
        "Respuesta:"
    )


def generate_answer(question: str, contexts: list[str]) -> str:
    llm = get_llm()
    prompt = build_prompt(question, contexts)
    output = llm(prompt, max_tokens=256, stop=["\n\n", "Pregunta:", "Contexto:"])
    return output["choices"][0]["text"].strip()
