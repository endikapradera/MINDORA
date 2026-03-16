# IA Educativa Offline - Core

Core local con FastAPI para IA offline + RAG.

## Estructura
- app/main.py: arranque de FastAPI
- app/api: endpoints HTTP
- app/services: lógica de negocio
- app/storage: manejo de ramas y archivos

## Ejecutar en local (dev)
1. Crear venv y activar
2. Instalar dependencias
3. Ejecutar el servidor

## Ejecutable
Usar PyInstaller con [core/pyinstaller.spec](core/pyinstaller.spec) y el entrypoint [core/run_server.py](core/run_server.py).

## Endpoints base
- GET /health
- GET /api/branches
- POST /api/branches
- POST /api/documents/ingest (multipart: branch + file)
- POST /api/query?branch=Nombre
- POST /api/ask?branch=Nombre
- (ask devuelve `sources` con citas de chunk/documento)
- GET /api/assistant/dictionary
- POST /api/assistant/learn-phrase
- POST /api/study/topic-pack?branch=Nombre
- POST /api/exams/generate?branch=Nombre (incluye `exam_type`: `test_simple`, `test_multiple`, `desarrollo`, `mixto`)
- POST /api/exams/export/pdf?branch=Nombre&exam_id=ID&kind=exam|answer_key
- POST /api/exams/export/docx?branch=Nombre&exam_id=ID&kind=exam|answer_key
- POST /api/exams/solve-upload (multipart: branch + file + top_k)
- POST /api/exams/simulation/start?branch=Nombre
- POST /api/exams/simulation/submit?branch=Nombre
- GET /api/exams/simulation/history?branch=Nombre&limit=30

## Variables de entorno
- IA_OFFLINE_BASE_DIR: ruta base de datos y ramas
- IA_OFFLINE_EMBEDDINGS_MODEL: nombre/ruta del modelo de embeddings
- IA_OFFLINE_LLM_PATH: ruta a modelo GGUF para llama.cpp
- IA_OFFLINE_LLM_CTX: tamaño de contexto
- IA_OFFLINE_LLM_THREADS: hilos

## Chat con memoria e intención
- `ask` acepta `session_id` para mantener historial conversacional por rama.
- `ask` acepta `response_style`: `auto`, `corta`, `detallada`, `pasos`, `detallada_pasos`.
- Puedes enseñar frases a la IA con `POST /api/assistant/learn-phrase`.

## OCR de imágenes
Para extraer texto de imágenes se usa `pytesseract`. Requiere instalar Tesseract en el sistema.

En macOS:
- `brew install tesseract`
- (opcional para español) descargar `spa.traineddata` en la carpeta `tessdata`.

