#!/usr/bin/env bash
# =============================================================================
#  MINDORA — build.sh
#  Builds a fully standalone desktop app on macOS, Windows (cross) or Linux.
#
#  Usage:
#    chmod +x build.sh
#    ./build.sh
#
#  Output (macOS):   ui/src-tauri/target/release/bundle/macos/MINDORA.dmg
#  Output (Windows): ui/src-tauri/target/release/bundle/nsis/*.exe
#  Output (Linux):   ui/src-tauri/target/release/bundle/appimage/*.AppImage
#                    ui/src-tauri/target/release/bundle/deb/*.deb
# =============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CORE="$ROOT/core"
UI="$ROOT/ui"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║          MINDORA — Build Standalone App          ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────
# 0. Pre-flight checks
# ─────────────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1  || { echo "❌ python3 not found"; exit 1; }
command -v cargo   >/dev/null 2>&1  || { echo "❌ cargo not found (install Rust from rustup.rs)"; exit 1; }
command -v node    >/dev/null 2>&1  || { echo "❌ node not found (install from nodejs.org)"; exit 1; }

python3 -m PyInstaller --version >/dev/null 2>&1 || {
  echo "📦 Installing PyInstaller..."
  python3 -m pip install pyinstaller --user -q
}
echo "✅ PyInstaller: $(python3 -m PyInstaller --version)"

# Detect OS
OS="$(uname -s)"
echo "🖥  Building on: $OS"

# ─────────────────────────────────────────────────────────────────
# 1. Copy embedding model into assets/ (if not already there)
# ─────────────────────────────────────────────────────────────────
EMB_DEST="$CORE/assets/embedding_model"

if [ ! -d "$EMB_DEST" ] || [ -z "$(ls -A "$EMB_DEST" 2>/dev/null)" ]; then
  echo "📥 Copying embedding model to assets/..."
  # Try paraphrase-multilingual first (current model), then all-MiniLM-L6-v2
  EMB_CACHE_MULTILINGUAL="$HOME/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
  EMB_CACHE_MINILM="$HOME/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"

  if [ -d "$EMB_CACHE_MULTILINGUAL" ]; then
    SNAP_HASH=$(cat "$EMB_CACHE_MULTILINGUAL/refs/main" 2>/dev/null || echo "")
    SNAP_DIR="$EMB_CACHE_MULTILINGUAL/snapshots/$SNAP_HASH"
  elif [ -d "$EMB_CACHE_MINILM" ]; then
    SNAP_HASH=$(cat "$EMB_CACHE_MINILM/refs/main" 2>/dev/null || echo "")
    SNAP_DIR="$EMB_CACHE_MINILM/snapshots/$SNAP_HASH"
  else
    echo "⚠️  Embedding model not cached locally. Downloading (requires internet, ~90MB)..."
    python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
    SNAP_HASH=$(cat "$EMB_CACHE_MULTILINGUAL/refs/main")
    SNAP_DIR="$EMB_CACHE_MULTILINGUAL/snapshots/$SNAP_HASH"
  fi

  mkdir -p "$EMB_DEST"
  cp -r "$SNAP_DIR/." "$EMB_DEST/"
  echo "✅ Embedding model ready ($(du -sh "$EMB_DEST" | cut -f1))"
else
  echo "✅ Embedding model already in assets/ ($(du -sh "$EMB_DEST" | cut -f1))"
fi

# ─────────────────────────────────────────────────────────────────
# 2. Build Python backend with PyInstaller
# ─────────────────────────────────────────────────────────────────
echo ""
echo "🔨 Building Python backend with PyInstaller..."
cd "$CORE"

# Select spec based on OS
if [[ "$OS" == "Darwin" ]]; then
  PYINSTALLER_SPEC="pyinstaller.spec"
  BACKEND_EXE="dist/IA_Core/IA_Core"
elif [[ "$OS" == "Linux" ]]; then
  PYINSTALLER_SPEC="pyinstaller_linux.spec"
  BACKEND_EXE="dist/IA_Core/IA_Core"
else
  # Windows (Git Bash / MSYS)
  PYINSTALLER_SPEC="pyinstaller_windows.spec"
  BACKEND_EXE="dist/IA_Core/IA_Core.exe"
fi

python3 -m PyInstaller "$PYINSTALLER_SPEC" --clean --noconfirm

if [ ! -f "$CORE/$BACKEND_EXE" ]; then
  echo "❌ PyInstaller failed — $BACKEND_EXE not found"
  exit 1
fi
echo "✅ Backend built: $(du -sh "$CORE/dist/IA_Core" | cut -f1)"

# ─────────────────────────────────────────────────────────────────
# 3. Build the Tauri desktop app
# ─────────────────────────────────────────────────────────────────
echo ""
echo "🔨 Building Tauri desktop app..."
cd "$UI"
npm install --silent

if [[ "$OS" == "Linux" ]]; then
  npm run tauri build -- --bundles appimage,deb
else
  npm run tauri build
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              ✅ Build complete!                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "📦 Installer location:"
if [[ "$OS" == "Darwin" ]]; then
  find "$UI/src-tauri/target/release/bundle" -name "*.dmg" 2>/dev/null && echo ""
  echo "→ Share the .dmg with your students."
  echo "   macOS model dir: ~/Documents/MINDORA/models/"
elif [[ "$OS" == "Linux" ]]; then
  find "$UI/src-tauri/target/release/bundle" -name "*.AppImage" 2>/dev/null && echo ""
  find "$UI/src-tauri/target/release/bundle" -name "*.deb" 2>/dev/null && echo ""
  echo "→ Share the .AppImage (universal) or .deb (Debian/Ubuntu) with your students."
  echo "   Linux model dir: ~/.local/share/MINDORA/models/"
else
  find "$UI/src-tauri/target/release/bundle" -name "*.exe" 2>/dev/null && echo ""
  echo "→ Share the .exe installer with your students."
  echo "   Windows model dir: %APPDATA%\\MINDORA\\models\\"
fi
echo ""
echo "⚠️  IMPORTANT: Students also need the LLM model (.gguf file)."
echo "   Model: mistral-7b-instruct-v0.2.Q4_K_M.gguf (~4.1GB)"
echo "   Download: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
echo ""
