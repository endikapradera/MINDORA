from __future__ import annotations

import os
import glob
from collections import defaultdict, deque
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router

app = FastAPI(title="IA Educativa Offline Core")

# ── Request size guard (50 MB max body) ─────────────────────────────────────
_MAX_BODY_BYTES = 50 * 1024 * 1024  # 50 MB
_RATE_WINDOW_SECONDS = 30
_RATE_MAX_REQUESTS = 120
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def limit_request_size(request: Request, call_next):  # type: ignore[type-arg]
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": "Archivo demasiado grande. El límite es 50 MB."},
        )

    # Local rate limiting (per client IP/window).
    client_ip = request.client.host if request.client else "unknown"
    bucket = _rate_buckets[client_ip]
    now = monotonic()
    while bucket and (now - bucket[0]) > _RATE_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"detail": "Demasiadas solicitudes. Espera unos segundos e inténtalo de nuevo."},
        )
    bucket.append(now)

    return await call_next(request)

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
    import sys as _sys
    llm_path = os.getenv("IA_OFFLINE_LLM_PATH", "")
    model_found = bool(llm_path) and llm_path != "__not_found__" and Path(llm_path).exists()

    home = Path.home()
    # Use OS-appropriate path
    if _sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        models_dir = (Path(appdata) / "MINDORA" / "models") if appdata else (home / "Documents" / "MINDORA" / "models")
    elif _sys.platform == "darwin":
        models_dir = home / "Documents" / "MINDORA" / "models"
    else:
        xdg = os.getenv("XDG_DATA_HOME")
        models_dir = (Path(xdg) / "MINDORA" / "models") if xdg else (home / ".local" / "share" / "MINDORA" / "models")

    # List any .gguf files the user may have in the expected location
    found_files = sorted(glob.glob(str(models_dir / "*.gguf")))

    return {
        "model_found": model_found,
        "model_path": llm_path if model_found else None,
        "expected_dir": str(models_dir),
        "gguf_files": found_files,
    }
