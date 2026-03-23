from __future__ import annotations

import glob
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn


def _resource_path(relative: str) -> Path:
    """Return path to a bundled resource, works both frozen and unfrozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative  # type: ignore[attr-defined]
    return Path(__file__).parent / relative


def _user_data_dir() -> Path:
    """Return OS-appropriate user data dir for MINDORA."""
    home = Path.home()
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "MINDORA"
        return home / "Documents" / "MINDORA"
    elif sys.platform == "darwin":
        return home / "Documents" / "MINDORA"
    else:
        # Linux: follow XDG Base Directory spec
        xdg = os.getenv("XDG_DATA_HOME")
        if xdg:
            return Path(xdg) / "MINDORA"
        return home / ".local" / "share" / "MINDORA"


def _find_llm_model(kind: str = "profesor") -> Optional[str]:
    """
    Search for a .gguf model file in standard locations.
    Priority:
      1. IA_OFFLINE_LLM_PATH env var (already set -> use it)
      2. ~/Documents/MINDORA/models/         (macOS/Windows)
      3. ~/.local/share/MINDORA/models/      (Linux XDG)
      4. ~/Desktop/MINDORA/models/ (legacy)
      5. Same directory as the executable
    """
    env_name = "IA_OFFLINE_CODE_LLM_PATH" if kind == "codigo" else "IA_OFFLINE_LLM_PATH"
    if os.getenv(env_name):
        return os.environ[env_name]

    home = Path.home()
    search_dirs: list = [
        home / "Documents" / "MINDORA" / "models",
        home / ".local" / "share" / "MINDORA" / "models",
        home / "Desktop" / "MINDORA" / "models",
        home / "Desktop" / "MINDORA" / "MINDORA" / "models",
        Path(sys.executable).parent,
    ]
    # Also add APPDATA-based path on Windows
    appdata = os.getenv("APPDATA")
    if appdata:
        search_dirs.insert(0, Path(appdata) / "MINDORA" / "models")

    preferred_patterns = [
        "*qwen*coder*.gguf",
        "*coder*.gguf",
    ] if kind == "codigo" else [
        "*qwen*instruct*.gguf",
        "*qwen*.gguf",
        "*.gguf",
    ]

    for d in search_dirs:
        if not d.exists():
            continue
        for pattern in preferred_patterns:
            hits = sorted(glob.glob(str(d / pattern)))
            if kind == "profesor":
                hits = [h for h in hits if "coder" not in Path(h).name.lower()] or hits
            if hits:
                return hits[0]
    return None


def main() -> None:
    # -- Thread / compatibility env vars --
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("MKL_SERVICE_FORCE_INTEL", "1")

    # -- Set user data dir so config.py uses correct path when frozen --
    if getattr(sys, "frozen", False) and not os.getenv("IA_OFFLINE_BASE_DIR"):
        data_dir = _user_data_dir() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["IA_OFFLINE_BASE_DIR"] = str(data_dir)
        print(f"[MINDORA] Data dir: {data_dir}", flush=True)

    # -- Bundled embedding model (PyInstaller only) --
    if getattr(sys, "frozen", False):
        bundled_emb = _resource_path("embedding_model")
        if bundled_emb.exists():
            os.environ["IA_OFFLINE_EMBEDDINGS_MODEL"] = str(bundled_emb)

    # -- Auto-discover LLM model --
    model_path = _find_llm_model("profesor")
    code_model_path = _find_llm_model("codigo")
    if model_path:
        os.environ["IA_OFFLINE_LLM_PATH"] = model_path
        print(f"[MINDORA] Main LLM model: {model_path}", flush=True)
    else:
        expected_dir = _user_data_dir() / "models"
        print(
            f"[MINDORA] WARNING: No .gguf model found. "
            f"Place your model in {expected_dir}",
            flush=True,
        )
        # Still start the server - endpoints will return a clear error
        os.environ.setdefault("IA_OFFLINE_LLM_PATH", "__not_found__")

    if code_model_path:
        os.environ["IA_OFFLINE_CODE_LLM_PATH"] = code_model_path
        print(f"[MINDORA] Code LLM model: {code_model_path}", flush=True)
    elif model_path:
        os.environ.setdefault("IA_OFFLINE_CODE_LLM_PATH", model_path)

    host = os.getenv("IA_OFFLINE_HOST", "127.0.0.1")
    port = int(os.getenv("IA_OFFLINE_PORT", "8000"))
    print(f"[MINDORA] Starting backend on {host}:{port}", flush=True)
    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="warning")


if __name__ == "__main__":
    main()
