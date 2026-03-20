# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
#  pyinstaller_linux.spec — Linux build spec for MINDORA IA_Core
#
#  Differences vs pyinstaller.spec (macOS):
#    - llama_cpp ships .so files in lib/ (same as macOS) but no .dylibs/
#    - faiss extension modules are .cpython-*.so
#    - No .dylibs/ subfolder concept — shared libs are in standard linux paths
#    - PyMuPDF fitz has .so extension files
#
#  Run from the core/ directory:
#    python -m PyInstaller pyinstaller_linux.spec --clean --noconfirm
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
    # Linux layout: lib/pythonX.Y/site-packages
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

# ── Native Linux binaries ────────────────────────────────────────────────────

# llama_cpp: .so files in lib/ subdirectory
LLAMA_SO_LIB  = sorted(glob(str(LLAMA_CPP_DIR / "lib" / "*.so*")))
LLAMA_SO_ROOT = sorted(glob(str(LLAMA_CPP_DIR / "*.so*")))

# faiss: .so extension modules
FAISS_SO = sorted(glob(str(FAISS_DIR / "_swigfaiss*.so*")))
if not FAISS_SO:
    FAISS_SO = sorted(glob(str(FAISS_DIR / "swigfaiss*.so*")))
FAISS_EXTRA_SO = sorted(glob(str(FAISS_DIR / "*.so*")))

binaries = []

# llama_cpp native .so files
for so_file in LLAMA_SO_LIB:
    binaries.append((str(Path(so_file)), "llama_cpp/lib"))
for so_file in LLAMA_SO_ROOT:
    binaries.append((str(Path(so_file)), "llama_cpp"))

# faiss native modules
for so_file in FAISS_SO:
    binaries.append((str(Path(so_file)), "faiss"))
for so_file in FAISS_EXTRA_SO:
    binaries.append((str(Path(so_file)), "faiss"))

# PyMuPDF native extension
if FITZ_DIR is not None:
    for so_file in glob(str(FITZ_DIR / "*.so*")):
        binaries.append((str(Path(so_file)), "fitz"))

# Deduplicate binaries list
seen_bins = set()
deduped_binaries = []
for item in binaries:
    if item[0] not in seen_bins:
        seen_bins.add(item[0])
        deduped_binaries.append(item)
binaries = deduped_binaries

# ── Data files to bundle ─────────────────────────────────────────────────────
datas = [
    (str(ASSETS_DIR / "embedding_model"), "embedding_model"),
    (str(SITE_PACKAGES / "sentence_transformers"), "sentence_transformers"),
    (str(SITE_PACKAGES / "tokenizers"), "tokenizers"),
]

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden_imports = [
    "fastapi", "fastapi.middleware.cors", "starlette", "starlette.middleware",
    "starlette.middleware.cors", "starlette.routing", "starlette.responses",
    "starlette.staticfiles", "starlette.datastructures", "starlette.background",
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "pydantic", "pydantic.networks", "pydantic.types", "pydantic_core",
    "sqlmodel", "sqlalchemy", "sqlalchemy.dialects.sqlite",
    "sqlalchemy.pool", "sqlalchemy.sql", "sqlalchemy.orm",
    "pypdf", "docx", "pptx",
    "reportlab", "reportlab.pdfgen", "reportlab.lib",
    "reportlab.lib.pagesizes", "reportlab.platypus",
    "multipart", "python_multipart",
    "pytesseract", "PIL", "PIL.Image",
    "fitz", "fitz.fitz",
    "faiss", "numpy", "numpy.core", "numpy.lib", "numpy.linalg",
    "sentence_transformers", "sentence_transformers.models",
    "transformers", "transformers.models", "tokenizers",
    "huggingface_hub", "huggingface_hub.file_download",
    "safetensors", "safetensors.torch",
    "llama_cpp",
    "torch", "torch.nn", "torch.nn.functional",
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
    upx=False,
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
