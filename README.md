# MINDORA — IA Educativa Offline ( EN DESARROLLO ) 

> Aplicación de escritorio para USO ESTUDIANTIL GRATUITO: sube apuntes, genera exámenes, responde preguntas y tutoriza alumnos. Todo funciona **sin internet** una vez instalada.

<p align="center">
  <img src="logo-MINDORA.png" alt="MINDORA Logo" width="300"/>
</p>

---

## � Últimas incorporaciones

### 🐛 Hotfix — Arranque de app (Mar 2026)
- **Corregido cuelgue al iniciar**: el bucle de polling de salud (`/health`) tenía bloques `try-catch` mal anidados que dejaban la app colgada indefinitamente en la pantalla de carga.  
  Reescrito con estructura correcta: máx. 50 intentos × 1.2 s (~60 s de timeout), salida limpia tanto en éxito como en fallo.

### ✅ Banco de tests — 108 pruebas automatizadas (Mar 2026)
- **Fixtures educativos reales**: temarios de matemáticas, programación y física en `core/tests/fixtures/` para pruebas con contenido real.
- **50 nuevos tests de integración** (`core/tests/test_integration.py`):
  - `TestBranchCRUD` (9): crear, listar y eliminar ramas con validación de errores.
  - `TestTextExtraction` (8): extracción y chunking de los tres temarios.
  - `TestDocumentIngest` (5): ingestión con embeddings y FAISS mockeados.
  - `TestExamGeneration` (6): generación de exámenes por materia.
  - `TestExamValidator` (6): validador de distractores y *confidence scoring*.
  - `TestFullLifecycle` (1): ciclo completo rama → ingestión → examen → simulacro → borrado.
  - `TestErrorValidation` (6): manejo de errores e inputs inválidos.
  - `TestBancoPreguntas` (9): banco de preguntas sobre matemáticas, programación y física.

### 🎨 Validación inline en formularios (Mar 2026)
- Sustituidos los mensajes de estado tipo *badge* por **validación inline por campo**: `branchNameError`, `fileError`, `questionError`, `examTopicError`, `learnPhraseError`.
- Añadido sistema de **toast de notificaciones** (`showToast`) para confirmaciones y errores importantes, en lugar de la tarjeta de "Estado" permanente.
- Nuevos estilos `.field-error`, `.input-error` y `.toast-notification` en `styles.css`.

### 🧠 Fase 5 — Fine-tuning LoRA (Feb 2026)
- Pipeline de dataset LoRA con ejemplos aprobados y exportación.
- Script `train_lora.py` con dependencias de fine-tuning.
- Autoload del adaptador LoRA en inferencia + estado de runtime visible en la UI.

### 📷 Fase 3 — OCR automático (Feb 2026)
- OCR automático en PDFs escaneados con **PyMuPDF + Tesseract**.
- Extracción de imágenes embebidas en documentos.

### 🤖 Fase 2 — Mejoras de respuesta (Feb 2026)
- Postproceso anti-robot: las respuestas no parecen generadas por máquina.
- *Few-shot templates* por modo de respuesta en `llm.py`.
- Nuevos modos: `profesor`, `compañero`, `examen`, `pasos`, `corta`, `detallada`.
- Aprendizaje por feedback del usuario (frases al diccionario personalizado).

### 🔍 Fase 1 — RAG estructurado (Ene 2026)
- Recuperación aumentada por recuperación (RAG) con fuentes citadas.
- FAISS + embeddings locales (`all-MiniLM-L6-v2`).
- Validador de distractores y *confidence scoring* por pregunta y examen resuelto.

---

## �📦 Descargar e instalar (usuarios finales)

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

## 💡 Idea de negocio: por qué MINDORA tiene potencial

MINDORA nace para resolver un problema real: estudiar con IA sin exponer datos personales ni depender de internet.

### Propuesta de valor

- **100% offline**: los apuntes y preguntas no salen del equipo del usuario.
- **Privacidad por diseño**: ideal para estudiantes, centros educativos y organizaciones con datos sensibles.
- **Especialización educativa**: no es un chat generalista; está centrada en temarios, estudio y evaluación.
- **Flujo completo en una sola app**: ingesta de documentos, RAG, simulacros y generación de exámenes.

### Por qué es una oportunidad

- Las plataformas grandes priorizan la nube y el uso masivo.
- MINDORA se posiciona en un nicho creciente: **IA local aplicada a educación**.
- La tecnología reciente (GGUF, cuantización, llama.cpp, embeddings locales) permite ofrecer buena experiencia en hardware de usuario.

### Ventaja competitiva

MINDORA combina funcionalidades que normalmente están separadas:

1. Tutor IA sobre documentos propios.
2. Generación de exámenes y solucionarios.
3. Simulacros evaluables con histórico de progreso.
4. Todo funcionando en local y con control de datos.

En resumen: puede posicionarse como **“asistente académico offline”** para estudiantes, opositores, academias y universidades.

---

## 📄 Licencia

Consulta el archivo [LICENSE](LICENSE) para más información.
