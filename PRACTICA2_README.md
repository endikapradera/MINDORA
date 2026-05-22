# MINDORA · Adaptación oficial a Práctica 2

Este documento describe cómo ejecutar y presentar MINDORA para cumplir la práctica de **Agente Multimodal local**.

## 1) Cumplimiento de requisitos

### Requisito: modo local/offline
- Backend local FastAPI (`127.0.0.1:8000`).
- LLM local por endpoint local compatible OpenAI:
  - Ollama (`127.0.0.1:11434/v1`)
  - LM Studio (`127.0.0.1:1234/v1`)

### Requisito: LangChain
- Orquestación de respuestas en `core/app/services/langchain_orchestrator.py`.
- Flujo conectado al motor de respuestas en `core/app/services/llm.py`.

### Requisito: 2+ tipos de entrada
- PDF, imagen (OCR), CSV, DOCX, PPTX, TXT/MD.
- Extracción en `core/app/services/text_extract.py`.

### Requisito: contexto conversacional
- Persistencia por sesión y rama en `core/app/services/chat_memory.py`.
- Integración en endpoint `ask`.

### Requisito: interfaz
- Demo Streamlit en `demo/streamlit_app.py`.

---

## 2) Instalación

```bash
cd MINDORA/core
python3 -m pip install -r requirements.txt
```

### Arranque backend
```bash
cd MINDORA
python3 core/run_server.py
```

### Arranque Streamlit
```bash
cd MINDORA
streamlit run demo/streamlit_app.py
```

---

## 3) Configuración de proveedor local LLM

## Opción A: Ollama (recomendada)
1. Arrancar Ollama.
2. Descargar modelo (ejemplo):
   - `ollama pull qwen2.5:7b`
3. Variables de entorno:

```bash
export IA_LANGCHAIN_ENABLED=1
export IA_LOCAL_LLM_PROVIDER=ollama
export IA_LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1
export IA_LOCAL_LLM_MODEL=qwen2.5:7b
```

## Opción B: LM Studio
1. Abrir LM Studio.
2. Cargar modelo y activar servidor local OpenAI-compatible.
3. Variables:

```bash
export IA_LANGCHAIN_ENABLED=1
export IA_LOCAL_LLM_PROVIDER=lmstudio
export IA_LOCAL_LLM_BASE_URL=http://127.0.0.1:1234/v1
export IA_LOCAL_LLM_MODEL=qwen2.5-7b-instruct
```

---

## 4) Escenarios de demo (3 obligatorios)

1. **PDF académico**
   - Ingesta de PDF.
   - Pregunta: resumen en 5 puntos + conclusión.

2. **Imagen/apunte escaneado**
   - Ingesta de imagen (OCR).
   - Pregunta de explicación sencilla y seguimiento.

3. **CSV**
   - Ingesta de CSV.
   - Pregunta de análisis de tendencias + recomendaciones.

---

## 5) Prompt engineering (resumen)

Se usan estilos de respuesta diferenciados (`auto`, `corta`, `detallada`, `pasos`, `examen`, `profesor`, `companero`) y reglas explícitas de:
- no alucinación,
- respuesta contextual,
- estructura legible.

---

## 6) Checklist final de entrega

- [ ] Repositorio actualizado con instrucciones claras.
- [ ] `requirements.txt` completo.
- [ ] Demo Streamlit funcional.
- [ ] 3 escenarios documentados con capturas.
- [ ] Memoria técnica 3-5 páginas (arquitectura, decisiones, prompts, mejoras).
- [ ] ZIP final validado en limpio.
