# MINDORA · Adaptación oficial a Práctica 2

Este documento resume cómo ejecutar, justificar y presentar MINDORA como entrega de la práctica de **Agente Multimodal local**. La versión final está centrada en una **app desktop offline** con backend local, LangChain y modelos ejecutados en la propia máquina.

## 1) Cumplimiento de requisitos

### Requisito: modo local/offline
- Backend local FastAPI en `127.0.0.1:8000`.
- LLM local mediante proveedor compatible OpenAI:
  - Ollama (`127.0.0.1:11434/v1`)
  - LM Studio (`127.0.0.1:1234/v1`)
- Datos, historial, índices y exámenes almacenados localmente.

### Requisito: LangChain
- Orquestación en [core/app/services/langchain_orchestrator.py](core/app/services/langchain_orchestrator.py).
- Integración con el flujo general de respuestas en [core/app/services/llm.py](core/app/services/llm.py).

### Requisito: 2 o más tipos de entrada
- PDF
- Imagen con OCR
- CSV
- DOCX / PPTX / TXT / MD

### Requisito: contexto conversacional
- Persistencia por sesión y rama en [core/app/services/chat_memory.py](core/app/services/chat_memory.py).
- Recuperación contextual con memoria reciente en el endpoint `ask`.

### Requisito: interfaz
- Interfaz principal en app desktop Tauri + React.
- Exámenes resueltos en directo dentro de la app.
- La entrega final ya no depende de Streamlit.

## 2) Instalación

### Backend
```bash
cd MINDORA/core
python3 -m pip install -r requirements.txt
```

### Frontend
```bash
cd MINDORA/ui
npm install
```

### Arranque backend
```bash
cd MINDORA
python3 core/run_server.py
```

### Arranque app desktop en desarrollo
```bash
cd MINDORA/ui
npm run tauri dev
```

### Build desktop macOS
```bash
cd MINDORA
./build.sh
```

## 3) Configuración de proveedor local LLM

### Opción A: Ollama
1. Arrancar Ollama.
2. Descargar un modelo compatible, por ejemplo:
   - `ollama pull qwen2.5:7b`
3. Variables de entorno recomendadas:

```bash
export IA_LANGCHAIN_ENABLED=1
export IA_LOCAL_LLM_PROVIDER=ollama
export IA_LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1
export IA_LOCAL_LLM_MODEL=qwen2.5:7b
```

### Opción B: LM Studio
1. Abrir LM Studio.
2. Cargar modelo.
3. Activar el servidor local OpenAI-compatible.

```bash
export IA_LANGCHAIN_ENABLED=1
export IA_LOCAL_LLM_PROVIDER=lmstudio
export IA_LOCAL_LLM_BASE_URL=http://127.0.0.1:1234/v1
export IA_LOCAL_LLM_MODEL=qwen2.5-7b-instruct
```

## 4) Escenarios de demo recomendados

### Escenario 1 — PDF académico
- Ingesta de PDF.
- Pregunta: “Resúmeme este documento en 5 puntos y una conclusión”.
- Follow-up: “Explícame el concepto X paso a paso”.

### Escenario 2 — Imagen / apunte escaneado
- Ingesta de imagen con OCR.
- Pregunta: “Extrae la idea principal y explícamela fácil”.
- Seguimiento: “Ahora dame 3 preguntas de repaso”.

### Escenario 3 — CSV
- Ingesta de CSV.
- Pregunta: “Analiza tendencias y dame recomendaciones accionables”.

### Escenario 4 — Examen en vivo
- Generación desde la pestaña Exámenes.
- Formato único tipo test A-B-C-D.
- Resolución inmediata en la propia app.

## 5) Prompt engineering y calidad de respuesta

La versión final utiliza reglas explícitas para:
- responder solo con el contexto recuperado,
- reconocer cuándo la evidencia es insuficiente,
- estructurar la respuesta de forma legible,
- adaptar el tono al modo seleccionado.

Mejoras añadidas en la fase final:
- evidencia extractiva previa al prompt,
- recuperación reforzada para consultas vagas o globales,
- guardrail de baja evidencia para evitar alucinación,
- respuesta final con referencias `[FUENTE n]`.

## 6) Exámenes

La aplicación final ha sido simplificada para el uso académico solicitado:
- solo genera exámenes **tipo test**,
- cada pregunta tiene exactamente 4 opciones: A, B, C y D,
- solo hay una respuesta correcta,
- la resolución se hace en el momento con feedback inmediato.

Se han eliminado los modos mixtos, de desarrollo y variantes heredadas.

## 7) Checklist final de entrega

- [x] Repositorio actualizado con instrucciones claras.
- [x] Dependencias del backend y frontend documentadas.
- [x] App desktop funcional desde GitHub.
- [x] Exámenes limitados a formato tipo test A-B-C-D.
- [x] Guía de práctica y guion de vídeo alineados con la versión actual.
- [ ] ZIP final validado en entorno limpio.
