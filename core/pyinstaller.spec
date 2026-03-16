# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import site
from glob import glob
from pathlib import Path

block_cipher = None

def _first_existing(candidates: list[Path]) -> Path:
    for p in candidates:
        if p.exists():
            return p
    raise RuntimeError(f"No existing path found in candidates: {candidates}")


def _collect_site_packages() -> list[Path]:
    paths: list[Path] = []
    try:
        paths.append(Path(site.getusersitepackages()))
    except Exception:
        pass
    try:
        for p in site.getsitepackages():
            paths.append(Path(p))
    except Exception:
        pass
    # fallback from interpreter layout
    paths.append(Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages")
    # dedupe while preserving order
    dedup: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(p)
    return dedup


SITE_CANDIDATES = _collect_site_packages()
SITE_PACKAGES = _first_existing(SITE_CANDIDATES)

LLAMA_CPP_DIR = _first_existing([p / "llama_cpp" for p in SITE_CANDIDATES])
FAISS_DIR = _first_existing([p / "faiss" for p in SITE_CANDIDATES])
ASSETS_DIR = Path("assets")

FAISS_SO_FILES = sorted(glob(str(FAISS_DIR / "_swigfaiss*.so")))
LLAMA_DYLIBS = sorted(glob(str(LLAMA_CPP_DIR / "lib" / "*.dylib")))

# ── Native binaries to bundle ───────────────────────────────────────────────
binaries = []

# llama_cpp native dylibs
for dylib in LLAMA_DYLIBS:
    binaries.append((str(Path(dylib)), "llama_cpp/lib"))

# faiss native modules
for so_file in FAISS_SO_FILES:
    binaries.append((str(Path(so_file)), "faiss"))

# faiss runtime dylibs
if (FAISS_DIR / ".dylibs").exists():
    for dylib in glob(str(FAISS_DIR / ".dylibs" / "*.dylib")):
        binaries.append((str(Path(dylib)), "faiss/.dylibs"))

# ── Data files to bundle ────────────────────────────────────────────────────
datas = [
    # Embedding model (all-MiniLM-L6-v2) — bundled offline, no internet needed
    (str(ASSETS_DIR / "embedding_model"), "embedding_model"),
    # sentence_transformers package resources
    (str(SITE_PACKAGES / "sentence_transformers"), "sentence_transformers"),
    # tokenizers + transformers data
    (str(SITE_PACKAGES / "tokenizers"), "tokenizers"),
]

# ── Hidden imports ──────────────────────────────────────────────────────────
hidden_imports = [
    # FastAPI / Starlette
    "fastapi", "fastapi.middleware.cors", "starlette", "starlette.middleware",
    "starlette.middleware.cors", "starlette.routing", "starlette.responses",
    "starlette.staticfiles", "starlette.datastructures", "starlette.background",
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    # Pydantic
    "pydantic", "pydantic.networks", "pydantic.types", "pydantic_core",
    # SQLModel / SQLAlchemy
    "sqlmodel", "sqlalchemy", "sqlalchemy.dialects.sqlite",
    "sqlalchemy.pool", "sqlalchemy.sql", "sqlalchemy.orm",
    # PDF / DOCX / PPTX
    "pypdf", "docx", "pptx",
    "reportlab", "reportlab.pdfgen", "reportlab.lib",
    "reportlab.lib.pagesizes", "reportlab.platypus",
    # Multipart
    "multipart", "python_multipart",
    # Tesseract
    "pytesseract", "PIL", "PIL.Image",
    # FAISS + numpy
    "faiss", "numpy", "numpy.core", "numpy.lib", "numpy.linalg",
    # Sentence transformers + HuggingFace
    "sentence_transformers", "sentence_transformers.models",
    "transformers", "transformers.models", "tokenizers",
    "huggingface_hub", "huggingface_hub.file_download",
    "safetensors", "safetensors.torch",
    # llama_cpp
    "llama_cpp",
    # Torch (used by sentence_transformers)
    "torch", "torch.nn", "torch.nn.functional",
    # Our app packages
    "app", "app.main", "app.api", "app.api.router",
    "app.api.routes", "app.api.routes.ask", "app.api.routes.assistant",
    "app.api.routes.branches", "app.api.routes.documents",
    "app.api.routes.exams", "app.api.routes.query", "app.api.routes.study",
    "app.schemas", "app.services", "app.storage",
    "anyio", "anyio._backends._asyncio", "anyio._backends._trio",
    "h11", "httptools", "watchfiles", "websockets",
    "click", "email_validator", "dnspython",
]

a = Analysis(
    ["run_server.py"],
    pathex=[str(Path(".").resolve())],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter", "notebook", "test"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IA_Core",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # upx can break native dylibs on macOS
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="IA_Core",
)
