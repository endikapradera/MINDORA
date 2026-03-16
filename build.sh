#!/usr/bin/env bash
# =============================================================================
#  MINDORA — build.sh
#  Builds a fully standalone desktop app (.dmg on macOS, .exe/.msi on Windows)
#  that students can install without Python, Node, or any technical knowledge.
#
#  Usage:
#    chmod +x build.sh
#    ./build.sh
#
#  Output:
#    ui/src-tauri/target/release/bundle/  ← installer lives here
#      macos/   → MINDORA.dmg
#      msi/     → MINDORA_1.0.0_x64_en-US.msi   (Windows only)
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

PYINSTALLER="$(python3 -m PyInstaller --version 2>/dev/null)" || {
  echo "📦 Installing PyInstaller..."
  python3 -m pip install pyinstaller --user -q
}
echo "✅ PyInstaller: $(python3 -m PyInstaller --version)"

# ─────────────────────────────────────────────────────────────────
# 1. Copy embedding model into assets/ (if not already there)
# ─────────────────────────────────────────────────────────────────
EMB_CACHE="$HOME/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"
EMB_DEST="$CORE/assets/embedding_model"

if [ ! -d "$EMB_DEST" ] || [ -z "$(ls -A "$EMB_DEST" 2>/dev/null)" ]; then
  echo "📥 Copying embedding model to assets/..."
  SNAP_HASH=$(cat "$EMB_CACHE/refs/main" 2>/dev/null || echo "")
  if [ -z "$SNAP_HASH" ]; then
    echo "⚠️  Embedding model not cached locally. Downloading (requires internet, ~87MB)..."
    python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
    SNAP_HASH=$(cat "$EMB_CACHE/refs/main")
  fi
  SNAP_DIR="$EMB_CACHE/snapshots/$SNAP_HASH"
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
python3 -m PyInstaller pyinstaller.spec --clean --noconfirm

if [ ! -f "$CORE/dist/IA_Core/IA_Core" ]; then
  echo "❌ PyInstaller failed — dist/IA_Core/IA_Core not found"
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
npm run tauri build

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              ✅ Build complete!                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "📦 Installer location:"
if [[ "$OSTYPE" == "darwin"* ]]; then
  find "$UI/src-tauri/target/release/bundle" -name "*.dmg" 2>/dev/null && echo ""
  echo "→ Share the .dmg with your students. Each alumno instala y ya funciona."
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  find "$UI/src-tauri/target/release/bundle" -name "*.msi" 2>/dev/null && echo ""
  echo "→ Share the .msi with your students."
fi
echo ""
echo "⚠️  IMPORTANT: Students also need to place the LLM model (.gguf) in:"
echo "   macOS:   ~/Documents/MINDORA/models/"
echo "   Windows: C:\\Users\\<name>\\Documents\\MINDORA\\models\\"
echo ""
echo "   Model: mistral-7b-instruct-v0.2.Q4_K_M.gguf (~4.1GB)"
echo "   Download: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF"
echo ""
