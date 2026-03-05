# IA Educativa Offline

Proyecto con core local (FastAPI) + UI desktop (Tauri + React).

## Carpetas
- core/: backend local IA + RAG
- ui/: interfaz desktop

## Flujo
1) Levantar core en localhost:8000
2) Levantar UI en localhost:1420 (dev) o empaquetar con Tauri

## Empaquetado
- Core: PyInstaller con [core/pyinstaller.spec](core/pyinstaller.spec)
- UI: build con Tauri en [ui/src-tauri](ui/src-tauri)
