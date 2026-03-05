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
- POST /api/exams/generate?branch=Nombre
- POST /api/exams/export/pdf?branch=Nombre&exam_id=ID
- POST /api/exams/export/docx?branch=Nombre&exam_id=ID

## Variables de entorno
- IA_OFFLINE_BASE_DIR: ruta base de datos y ramas
- IA_OFFLINE_EMBEDDINGS_MODEL: nombre/ruta del modelo de embeddings
- IA_OFFLINE_LLM_PATH: ruta a modelo GGUF para llama.cpp
- IA_OFFLINE_LLM_CTX: tamaño de contexto
- IA_OFFLINE_LLM_THREADS: hilos

