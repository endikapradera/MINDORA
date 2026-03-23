# Installation Guide for GitHub Users

## 🚀 Quick Start for Cloning from GitHub

If you're cloning MINDORA from GitHub, follow these steps:

```bash
# Clone the repository
git clone https://github.com/endikapradera/MINDORA.git
cd MINDORA/MINDORA

# Run the automated installer (macOS/Linux)
chmod +x install.sh
./install.sh

# For Windows (Git Bash)
# bash install.sh
```

## ✅ What the `install.sh` Script Does

1. ✓ Verifies Python 3.9+, Node.js 16+, Git installed
2. ✓ Installs frontend dependencies (`npm install`)
3. ✓ Compiles frontend (`npm run build`)
4. ✓ Installs Python dependencies (`pip3 install -r requirements.txt`)
5. ✓ Creates models directory
6. ✓ Prompts for model downloads if needed
7. ✓ Optionally runs tests to verify everything works

## 📥 Model Setup (Required)

### Automatic (Recommended)
The `install.sh` script will guide you through downloading models.

### Manual Download

**Qwen 2.5-7B-Instruct** (4.4 GB)
- Download: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
- Save as: `Qwen2.5-7B-Instruct-Q4_K_M.gguf`

**Devstral-Small** (13 GB)
- Download: https://huggingface.co/mistralai/Devstral-Small-2505_gguf
- Save as: `devstralQ4_K_M.gguf`

**Place in:**
```
~/Documents/MINDORA/models/  (macOS/Windows)
~/.local/share/MINDORA/models/  (Linux)
```

## 🔧 Manual Setup (If Not Using install.sh)

### 1. Frontend
```bash
cd ui
npm install
npm run build
cd ..
```

### 2. Backend
```bash
pip3 install -r requirements.txt
```

### 3. Models
```bash
mkdir -p ~/Documents/MINDORA/models
# Download and place model files there
```

## 🚀 Running MINDORA

### Terminal 1 - Backend
```bash
python3 core/run_server.py
```

Expected output:
```
[MINDORA] Main LLM model: ~/Documents/MINDORA/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
[MINDORA] Code LLM model: ~/Documents/MINDORA/models/devstralQ4_K_M.gguf
[MINDORA] Starting backend on 127.0.0.1:8000
```

### Terminal 2 - Run Tests
```bash
python3 core/test_temario_qa.py
```

Expected result:
```
✓ Total: 30/30 tests pasaron (100%)
```

## 🌐 API Usage

### Health Check
```bash
curl http://127.0.0.1:8000/health
# Returns: {"status":"ok"}
```

### Ask a Question
```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is artificial intelligence?",
    "response_style": "corta"
  }' \
  -G -d "branch=principal"
```

### Response Styles
- `auto` - Automatic
- `corta` - Short answer
- `detallada` - Detailed explanation
- `pasos` - Step-by-step guide
- `examen` - Q&A format
- `profesor` - Academic language
- `companero` - Conversational tone
- `codigo` - Code-focused

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Ensure backend is running in terminal 1 |
| `ModuleNotFoundError` | Run `pip3 install -r requirements.txt` |
| `Models not found` | Download models and place in correct directory |
| `Port 8000 in use` | Run `pkill -f run_server` or change port |
| `npm not found` | Install Node.js from https://nodejs.org/ |
| `python3 not found` | Install Python 3.9+ from https://python.org/ |

## 📚 Documentation

- **QUICK_START.md** - 30-second reference
- **README_COMPLETO.md** - Comprehensive guide
- **TEST_REPORT.md** - Testing results
- **INSTALL.md** - Installation details

## ✅ System Requirements

- **macOS**: 10.13+
- **Windows**: 10 Build 1909+
- **Linux**: Modern distribution (Ubuntu 20.04+)
- **RAM**: 8 GB minimum (16+ GB recommended)
- **Disk**: 30 GB (for models)

## 🔗 Links

- **GitHub**: https://github.com/endikapradera/MINDORA
- **Qwen Models**: https://huggingface.co/Qwen/
- **Devstral Models**: https://huggingface.co/mistralai/
- **FastAPI Docs**: http://127.0.0.1:8000/docs (when server running)

## 🎓 Educational Use

MINDORA is designed for educational purposes with offline AI:
- Teacher-assisted learning
- Personal study assistant
- Exam preparation
- Document analysis
- Code assistance

## 📞 Support

If you encounter issues:
1. Check this guide
2. Review logs: `/tmp/mindora_backend.log`
3. Verify all requirements are installed
4. Check GitHub issues
5. Review TEST_REPORT.md for diagnostics

## ✨ Verification

After installation, verify everything works:

```bash
# 1. Backend responds
curl http://127.0.0.1:8000/health

# 2. Run tests
python3 core/test_temario_qa.py

# 3. Ask a question
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello, what is MINDORA?","response_style":"corta"}' \
  -G -d "branch=principal"
```

**✅ Installation complete!** MINDORA is ready to use.

---

*MINDORA v1.0 - Offline Educational AI*  
*Last updated: 2026-03-23*

