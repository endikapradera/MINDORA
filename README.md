# MINDORA

Aplicación de escritorio educativa **offline** (Tauri + React + FastAPI + LLM local).

## 1) Qué es

MINDORA permite:
- crear ramas de estudio por asignatura,
- ingerir apuntes (PDF/DOCX/PPTX/TXT/MD e imagen con OCR),
- chatear con RAG y memoria local,
- generar/corregir exámenes y simulacros,
- funcionar sin nube para contenido sensible.

---

## 2) Arquitectura técnica

- **UI Desktop**: Tauri v1 + React + TypeScript + Vite
- **Core IA**: FastAPI local en `127.0.0.1:8000`
- **RAG**: embeddings locales + FAISS + reranking híbrido
- **LLM local**: `llama-cpp-python` (GGUF)
- **Persistencia**: SQLite + archivos por rama/sesión

Estructura principal:

- `core/app/main.py`: API y middlewares (CORS, límites)
- `core/app/api/routes/*`: endpoints REST
- `core/app/services/*`: extracción, RAG, exámenes, memoria chat
- `core/run_server.py`: entrypoint del backend empaquetado
- `ui/src/App.tsx`: UI principal
- `ui/src/api.ts`: cliente HTTP
- `ui/src-tauri/src/main.rs`: arranque app y sidecar backend
- `build.sh`: build local multiplataforma (según host)

---

## 3) Requisitos

### Comunes
- Python 3.9+
- Node 18+
- Rust (rustup)

### OCR
- Tesseract instalado en sistema

### Modelo LLM
- Archivo GGUF, recomendados:
   - `qwen2.5-7b-instruct` (principal)
   - `devstral` (código, opcional)

Ubicación del modelo por OS:
- macOS: `~/Documents/MINDORA/models/`
- Windows: `%APPDATA%/MINDORA/models/`
- Linux: `~/.local/share/MINDORA/models/`

---

## 4) Instalación para desarrollo

Desde la raíz del repo:

1. Backend
   - `cd core`
   - `python3 -m pip install -r requirements.txt`

2. Frontend
   - `cd ../ui`
   - `npm install`

## 5) Instalación de modelos de IA

Los modelos se descargan automáticamente la primera vez que MINDORA los necesita, o puedes descargarlos manualmente:

### Descarga manual (recomendado)

```bash
# Crea la carpeta de modelos según tu OS:

# macOS
mkdir -p ~/Documents/MINDORA/models

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:APPDATA\MINDORA\models"

# Linux
mkdir -p ~/.local/share/MINDORA/models
```

### Modelos necesarios:

1. **Qwen 2.5 7B Instruct** (educación)
   - Descarga: https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF
   - Archivo: `Qwen2.5-7B-Instruct-Q4_K_M.gguf` (4.4 GB)

2. **Devstral Small 2505** (código, opcional pero recomendado)
   - Descarga: https://huggingface.co/mistralai/Devstral-Small-2505_gguf
   - Archivo: `devstralQ4_K_M.gguf` (13 GB)

Copia ambos archivos a la carpeta de modelos y reinicia MINDORA.

3. Ejecutar en dev
   - Terminal 1: backend (FastAPI/Uvicorn)
   - Terminal 2: `npm run dev` en `ui`

> Si se usa empaquetado desktop, Tauri lanza el backend sidecar automáticamente.

---

## 5) Seguridad aplicada

- CSP en Tauri (solo recursos locales y `127.0.0.1`)
- `shell.execute = false` (sin ejecución arbitraria de comandos)
- `fs.scope` restringido a rutas de MINDORA/usuario
- Límite de tamaño por request (50 MB)
- Rate limiting local por cliente (ventana corta)
- Política offline: sin dependencia de APIs externas para respuesta

---

## 6) Funciones implementadas recientes

- Soporte de build Linux (`pyinstaller_linux.spec`, workflow Linux)
- Rutas de datos y modelos cross-platform (macOS/Windows/Linux)
- Historial de chat persistente con:
  - listar,
  - cargar,
  - eliminar,
  - renombrar,
  - fijar (pin),
  - búsqueda
- Guardado de conversación a `.txt`
- Deduplicación de headers/footers repetidos en PDF
- Guardrail de baja evidencia en `ask`: responde “no lo sé con certeza”

---

## 7) Testing y validación

### Backend
- `cd core`
- `python3 -m pytest -q`

Estado actual: **110 passed**.

### Frontend
- `cd ui`
- `npx tsc --noEmit`
- `npm run build`

Estado actual: build OK.

---

## 8) Build instalable

### Build local (host actual)
- `./build.sh`

Genera según plataforma:
- macOS: `.dmg`
- Windows: `.exe` (NSIS)
- Linux: `.AppImage` y `.deb`

### CI
- `.github/workflows/build-windows.yml`
- `.github/workflows/build-linux.yml`

---

## 9) Release checklist

1. Tests backend OK
2. Typecheck + build frontend OK
3. Build instaladores OK
4. Verificar arranque en máquina limpia por OS
5. Publicar artefactos en GitHub Releases

---

## 10) Troubleshooting rápido

- **No encuentra modelo GGUF**: revisar ruta por SO en sección 3
- **OCR no funciona**: instalar Tesseract y reiniciar app
- **Build falla en Linux**: instalar dependencias del workflow localmente (webkit2gtk/gtk/openblas)
- **Respuesta pobre**: aumentar material ingerido o hacer pregunta más específica

---

## 11) Licencia

Ver `LICENSE`.
