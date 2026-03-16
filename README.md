# MINDORA — IA Educativa Offline ( EN DESARROLLO ) 

> Aplicación de escritorio para USO ESTUDIANTIL GRATUITO: sube apuntes, genera exámenes, responde preguntas y tutoriza alumnos. Todo funciona **sin internet** una vez instalada.

<p align="center">
  <img src="logo-MINDORA.png" alt="MINDORA Logo" width="300"/>
</p>

---

## 📦 Descargar e instalar (usuarios finales)

| Plataforma | Descarga | Requisitos |
|------------|----------|------------|
| **macOS** (Apple Silicon) | [Releases → .dmg](../../releases) | macOS 12+ |
| **Windows** (x64) | [Releases → .exe](../../releases) | Windows 10/11 x64 |

### ⚠️ Modelo LLM — descarga obligatoria (una sola vez, ~4.1 GB)

Antes de arrancar la app por primera vez, coloca este archivo en tu carpeta de Documentos:

- **macOS**: `~/Documents/MINDORA/models/mistral-7b-instruct-v0.2.Q4_K_M.gguf`
- **Windows**: `C:\Users\<tu nombre>\Documents\MINDORA\models\mistral-7b-instruct-v0.2.Q4_K_M.gguf`

Descárgalo de: [HuggingFace — Mistral 7B Instruct Q4_K_M](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)

---

## 🚀 Publicar una nueva versión (solo para el desarrollador)

### 1. Obtener el instalador de Windows

1. Ve a **[Actions → Build Windows Installer](../../actions/workflows/build-windows.yml)**
2. Espera a que el workflow termine con ✅ (~20-30 min la primera vez)
3. Entra al workflow completado → sección **Artifacts** → descarga `MINDORA-Windows-xxxx.exe`

### 2. Publicar el Release en GitHub

1. Ve a **[Releases → Create a new release](../../releases/new)**
2. Pon el tag de versión: `v1.0.0`
3. Escribe el título: `MINDORA v1.0.0`
4. Adjunta los dos archivos:
   - `MINDORA_1.0.0_aarch64.dmg` (macOS — generado con `./build.sh` en tu Mac)
   - `MINDORA_1.0.0_x64-setup.exe` (Windows — descargado de Actions en el paso anterior)
5. Publica el release

Desde ese momento cualquier usuario puede ir a la página de Releases y descargar el instalador de su plataforma.

---

## 🏗️ Compilar desde código fuente

### macOS (Apple Silicon / Intel)

```bash
# Requisitos: Python 3.9+, Node 18+, Rust (rustup.rs)
chmod +x build.sh
./build.sh
# → Genera ui/src-tauri/target/release/bundle/dmg/MINDORA_1.0.0_aarch64.dmg
```

### Windows — vía GitHub Actions (recomendado)

La forma más sencilla es dejar que GitHub compile por ti:

1. Haz un push a `main`
2. Ve a **Actions** → **Build Windows Installer**
3. Descarga el artefacto `MINDORA-Windows-*.exe` cuando el workflow termine (~20-30 min)

> Workflow: [.github/workflows/build-windows.yml](.github/workflows/build-windows.yml)

### Windows — manual (desde una máquina Windows)

```powershell
# Requisitos: Python 3.11, Node 18+, Rust, VS Build Tools 2022
cd core
pip install -r requirements.txt pyinstaller
python -m PyInstaller pyinstaller_windows.spec --clean --noconfirm
cd ..\ui
npm install
npm run tauri build
# → ui/src-tauri/target/release/bundle/nsis/MINDORA_1.0.0_x64-setup.exe
```

---

## 🗂️ Estructura del proyecto

```
MINDORA/
├── build.sh                        ← Build completo (macOS)
├── .github/workflows/
│   └── build-windows.yml           ← GitHub Actions: compila Windows
├── core/                           ← Backend Python (FastAPI)
│   ├── app/
│   │   ├── api/routes/             ← Endpoints REST
│   │   ├── services/               ← LLM, embeddings, exámenes
│   │   └── storage/                ← Ramas, documentos, FAISS
│   ├── pyinstaller.spec            ← Spec PyInstaller macOS
│   ├── pyinstaller_windows.spec    ← Spec PyInstaller Windows
│   ├── requirements.txt
│   └── run_server.py
└── ui/                             ← Frontend Tauri + React + TypeScript
    ├── src/App.tsx                 ← Componente principal
    ├── src/api.ts                  ← Llamadas al backend
    └── src-tauri/
        ├── src/main.rs             ← Rust: lanza backend
        ├── tauri.conf.json
        └── icons/                  ← Iconos (todas las plataformas)
```

---

## ✨ Características

- 📚 **Ramas (temarios)**: crea ramas por asignatura, sube PDFs, Word, PowerPoint
- 🤖 **Chat IA**: pregunta sobre los apuntes, respuestas sin internet
- 📝 **Generador de exámenes**: tipo test, desarrollo o mixto, ajustable por dificultad
- 🔍 **Búsqueda semántica**: FAISS + embeddings locales (all-MiniLM-L6-v2)
- 💬 **Asistente**: conversación libre sobre el contenido subido
- 🗑️ **Gestión de ramas**: crea, selecciona y elimina con confirmación

---

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite |
| Desktop shell | Tauri v1 (Rust) |
| Backend API | FastAPI + Uvicorn |
| LLM local | llama-cpp-python (Mistral 7B Q4) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | FAISS |
| Empaquetado | PyInstaller + NSIS (Windows) / hdiutil (macOS) |

---

## 📄 Licencia

Consulta el archivo [LICENSE](LICENSE) para más información.
