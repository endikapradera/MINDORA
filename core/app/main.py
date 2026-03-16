from __future__ import annotations

import os
import glob
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

app = FastAPI(title="IA Educativa Offline Core")

# Allow all localhost / Tauri origins — this is a local-only app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        # Tauri production webview origins
        "tauri://localhost",
        "https://tauri.localhost",
        "null",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/setup/status")
def setup_status():
    """Returns whether the LLM model is found and the expected install path."""
    llm_path = os.getenv("IA_OFFLINE_LLM_PATH", "")
    model_found = bool(llm_path) and llm_path != "__not_found__" and Path(llm_path).exists()

    home = Path.home()
    models_dir = str(home / "Documents" / "MINDORA" / "models")

    # List any .gguf files the user may have in the expected location
    found_files = sorted(glob.glob(str(home / "Documents" / "MINDORA" / "models" / "*.gguf")))

    return {
        "model_found": model_found,
        "model_path": llm_path if model_found else None,
        "expected_dir": models_dir,
        "gguf_files": found_files,
    }
