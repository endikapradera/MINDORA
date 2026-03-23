# MINDORA - GUÍA RÁPIDA DE REFERENCIA

## 🚀 Iniciar el Sistema (30 segundos)

```bash
cd /Users/endikapraderatouzani/Desktop/MINDORA/MINDORA
python3 core/run_server.py
```

Esperarás este mensaje:
```
[MINDORA] Starting backend on 127.0.0.1:8000
```

## 🧪 Ejecutar Tests (en otra terminal)

```bash
cd /Users/endikapraderatouzani/Desktop/MINDORA/MINDORA
python3 core/test_temario_qa.py
```

Resultado esperado:
```
✓ Total: 30/30 tests pasaron (100%)
```

## 💬 Hacer una Pregunta Rápida

**Opción 1: Con curl**
```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué es IA?","response_style":"corta"}' \
  -G -d "branch=principal"
```

**Opción 2: Con Python**
```python
import requests

response = requests.post(
    'http://127.0.0.1:8000/api/ask',
    json={
        'question': '¿Qué es inteligencia artificial?',
        'response_style': 'corta'
    },
    params={'branch': 'principal'}
)
print(response.json()['answer'])
```

## 📊 Estilos de Respuesta Disponibles

| Estilo | Descripción |
|--------|-------------|
| `auto` | Automático (recomendado) |
| `corta` | 1-2 párrafos |
| `detallada` | Explicación completa |
| `pasos` | Guía paso a paso |
| `examen` | Formato Q&A |
| `profesor` | Lenguaje académico |
| `companero` | Conversacional |
| `codigo` | Especializado en programación |

## 📍 Ubicaciones Importantes

| Ruta | Descripción |
|------|-------------|
| `~/Documents/MINDORA/models/` | Modelos GGUF instalados |
| `~/Desktop/MINDORA/MINDORA/` | Proyecto principal |
| `~/Desktop/MINDORA/TEMARIO/` | Base de conocimiento |
| `https://github.com/endikapradera/MINDORA` | Repositorio |

## ✅ Checklist de Verificación

- [ ] Modelos presentes: `ls ~/Documents/MINDORA/models/` (debe mostrar 2 archivos .gguf)
- [ ] Backend inicia: `python3 core/run_server.py` (sin errores)
- [ ] API responde: `curl http://127.0.0.1:8000/health` (status 200)
- [ ] Tests pasan: `python3 core/test_temario_qa.py` (30/30)

## 🐛 Troubleshooting Rápido

**Problema: "Connection refused on 127.0.0.1:8000"**
→ Asegurate de que el servidor está corriendo en otra terminal

**Problema: "ModuleNotFoundError: No module named 'fastapi'"**
→ Instala dependencias: `pip3 install -r requirements.txt`

**Problema: "No se encuentran modelos"**
→ Verifica: `ls ~/Documents/MINDORA/models/` (debe tener 2 archivos)

**Problema: "Puerto 8000 en uso"**
→ Cambia puerto en `core/app/main.py` o mata proceso: `pkill -f run_server`

## 📈 Monitoreo en Vivo

```bash
# Ver logs del backend en tiempo real
tail -f /tmp/mindora_backend.log

# Ver procesos Python activos
ps aux | grep python3

# Ver conexiones de red
netstat -an | grep 8000
```

## 📚 Documentación Completa

Consulta estos archivos para más detalles:
- `README_COMPLETO.md` - Guía exhaustiva (800+ líneas)
- `TEST_REPORT.md` - Resultados de testing detallados
- `RESUMEN_FINAL.md` - Estado actual del sistema

## 🔗 Enlaces Útiles

- **GitHub**: https://github.com/endikapradera/MINDORA
- **Qwen Docs**: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
- **Devstral Docs**: https://huggingface.co/mistralai/Devstral-Small-2505_gguf
- **FastAPI Docs**: http://127.0.0.1:8000/docs (cuando servidor corre)

## 💡 Ejemplos Completos

### Pregunta Simple
```bash
python3 -c "
import requests
r = requests.post('http://127.0.0.1:8000/api/ask',
    json={'question': '¿Qué es un algoritmo?'},
    params={'branch': 'principal'})
print(r.json()['answer'])
"
```

### Pregunta de Código
```bash
python3 -c "
import requests
r = requests.post('http://127.0.0.1:8000/api/ask',
    json={'question': 'Escribe un algoritmo de búsqueda binaria',
          'response_style': 'codigo'},
    params={'branch': 'principal'})
print(r.json()['answer'])
"
```

### Pregunta Detallada
```bash
python3 -c "
import requests
r = requests.post('http://127.0.0.1:8000/api/ask',
    json={'question': 'Explica el concepto de herencia en OOP',
          'response_style': 'detallada'},
    params={'branch': 'principal'})
print(r.json()['answer'])
"
```

## 📞 Información del Sistema

**Versión**: 1.0  
**Modelos**:
- Principal: Qwen 2.5-7B-Instruct (4.4 GB)
- Código: Devstral-Small (13 GB)

**API**: FastAPI + Uvicorn  
**Puerto**: 8000  
**Protocolo**: HTTP REST  

**Soporte**: Consulta TEST_REPORT.md para detalles técnicos

---

*Última actualización: $(date '+%Y-%m-%d')*  
*MINDORA v1.0 - IA Educativa Offline*

