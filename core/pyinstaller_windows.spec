# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
#  pyinstaller_windows.spec — Windows build spec for MINDORA IA_Core
#
#  Differences vs pyinstaller.spec (macOS):
#    - llama_cpp ships .dll files (not .dylib)
#    - faiss extension modules are .pyd (not .so)
#    - Windows uses Lib/site-packages (capital L)
#    - No .dylibs/ subfolder concept
#
#  Run from the core/ directory:
#    python -m PyInstaller pyinstaller_windows.spec --clean --noconfirm
# =============================================================================

import sys
import os
import site
from glob import glob
from pathlib import Path

block_cipher = None


def _collect_site_packages() -> list:
    paths = []
    try:
        paths.append(Path(site.getusersitepackages()))
    except Exception:
        pass
    try:
        for p in site.getsitepackages():
            paths.append(Path(p))
    except Exception:
        pass
    # Windows layout: Lib/site-packages (capital L)
    paths.append(Path(sys.prefix) / "Lib" / "site-packages")
    # Linux/macOS fallback (in case running in WSL or similar)
    paths.append(
        Path(sys.prefix)
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    # Deduplicate while preserving order; skip non-existing paths
    dedup, seen = [], set()
    for p in paths:
        key = str(p)
        if key not in seen and p.exists():
            seen.add(key)
            dedup.append(p)
    return dedup


def _first_existing(candidates: list) -> Path:
    for p in candidates:
        if p.exists():
            return p
    raise RuntimeError(f"No existing path found in candidates: {candidates}")


SITE_CANDIDATES = _collect_site_packages()
SITE_PACKAGES   = _first_existing(SITE_CANDIDATES)
LLAMA_CPP_DIR   = _first_existing([p / "llama_cpp" for p in SITE_CANDIDATES])
FAISS_DIR       = _first_existing([p / "faiss"     for p in SITE_CANDIDATES])
FITZ_DIR_CANDIDATES = [p / "fitz" for p in SITE_CANDIDATES]
FITZ_DIR        = next((p for p in FITZ_DIR_CANDIDATES if p.exists()), None)
ASSETS_DIR      = Path("assets")

# ── Native Windows binaries ──────────────────────────────────────────────────

# llama_cpp: DLLs can live in lib/ sub-directory or directly in the package root
LLAMA_DLLS_LIB  = sorted(glob(str(LLAMA_CPP_DIR / "lib" / "*.dll")))
LLAMA_DLLS_ROOT = sorted(glob(str(LLAMA_CPP_DIR / "*.dll")))

# faiss: extension modules are .pyd on Windows
FAISS_PYD = sorted(glob(str(FAISS_DIR / "_swigfaiss*.pyd")))
if not FAISS_PYD:                                    # some builds omit leading _
    FAISS_PYD = sorted(glob(str(FAISS_DIR / "swigfaiss*.pyd")))
FAISS_DLLS = sorted(glob(str(FAISS_DIR / "*.dll")))  # any shipped DLLs

binaries = []

for dll in LLAMA_DLLS_LIB:
    binaries.append((dll, "llama_cpp/lib"))

for dll in LLAMA_DLLS_ROOT:
    binaries.append((dll, "llama_cpp"))

for pyd in FAISS_PYD:
    binaries.append((pyd, "faiss"))

for dll in FAISS_DLLS:
    binaries.append((dll, "faiss"))

# PyMuPDF native extension
if FITZ_DIR is not None:
    for pyd in glob(str(FITZ_DIR / "*.pyd")):
        binaries.append((pyd, "fitz"))
    for dll in glob(str(FITZ_DIR / "*.dll")):
        binaries.append((dll, "fitz"))

# ── Data files ───────────────────────────────────────────────────────────────
datas = [
    (str(ASSETS_DIR / "embedding_model"),          "embedding_model"),
    (str(SITE_PACKAGES / "sentence_transformers"), "sentence_transformers"),
    (str(SITE_PACKAGES / "tokenizers"),            "tokenizers"),
]

# ── Hidden imports (same as macOS spec) ─────────────────────────────────────
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
    # Tesseract + OCR
    "pytesseract", "PIL", "PIL.Image",
    # PyMuPDF (PDF render for OCR fallback)
    "fitz", "fitz.fitz",
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
    # App packages
    "app", "app.main", "app.api", "app.api.router",
    "app.api.routes", "app.api.routes.ask", "app.api.routes.assistant",
    "app.api.routes.branches", "app.api.routes.documents",
    "app.api.routes.exams", "app.api.routes.query", "app.api.routes.study",
    "app.schemas", "app.services", "app.storage",
    # Async / HTTP internals
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
    upx=False,      # UPX can corrupt DLLs on Windows — keep off
    console=True,   # Keep console visible so backend errors are debuggable
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
