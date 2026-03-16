# 📚 MINDORA — Guía de instalación para alumnos

## ¿Qué necesitas?

1. **El instalador de MINDORA** (.dmg en Mac, .exe en Windows) — te lo da tu profesor
2. **El modelo de IA** (archivo `.gguf`, ~4.1 GB) — descarga o cópialo de una memoria USB

---

## Instalación en macOS

### Paso 1 — Instalar la app
1. Abre el archivo `MINDORA-1.0.0.dmg`
2. Arrastra `MINDORA` a la carpeta **Aplicaciones**
3. La primera vez que abras la app, haz **clic derecho → Abrir** (para saltarte el aviso de seguridad)

### Paso 2 — Colocar el modelo de IA
1. Abre **Finder** → ve a tu carpeta `Documentos`
2. Crea la carpeta: `Documentos/MINDORA/models/`
3. Copia el archivo `.gguf` dentro de esa carpeta

```
~/Documents/MINDORA/models/
    └── mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

### Paso 3 — Abrir MINDORA
1. Abre la app desde Aplicaciones
2. Verás una pantalla de carga mientras arranca la IA (10-20 segundos)
3. Si la IA no detecta el modelo, te mostrará exactamente dónde colocarlo
4. ¡Listo! Crea una rama con tu nombre y empieza a subir tus apuntes

---

## Instalación en Windows

### Paso 1 — Instalar la app
1. Ejecuta `MINDORA_1.0.0_x64_en-US.msi`
2. Acepta la instalación → la app se añade al Menú Inicio

### Paso 2 — Colocar el modelo de IA
1. Abre el Explorador de archivos → ve a `Documentos`
2. Crea la carpeta: `Documentos\MINDORA\models\`
3. Copia el archivo `.gguf` dentro de esa carpeta

```
C:\Users\TuNombre\Documents\MINDORA\models\
    └── mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

### Paso 3 — Abrir MINDORA
1. Busca "MINDORA" en el Menú Inicio
2. La primera vez puede tardar ~30 segundos en cargar la IA
3. ¡Listo!

---

## Primeros pasos en MINDORA

```
1. Crear rama → ponle tu nombre o el nombre de la asignatura
2. Subir apuntes → sube PDFs, Word, imágenes (foto de apuntes) o PPTX
3. Preguntar → escribe cualquier pregunta sobre el temario
4. Generar examen → elige dificultad, tipo y número de preguntas
5. Simulacro → practica con tiempo limitado y recibe nota automática
```

---

## Dónde descargar el modelo de IA

👉 [TheBloke/Mistral-7B-Instruct-v0.2-GGUF](https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF)

Descarga el archivo: `mistral-7b-instruct-v0.2.Q4_K_M.gguf` (~4.1 GB)

> Tu profesor puede proporcionarte el modelo en una memoria USB para no tener que descargarlo.

---

## Preguntas frecuentes

**¿Necesito internet para usar MINDORA?**  
No. Todo funciona completamente offline una vez instalado.

**¿Mis apuntes y datos son privados?**  
Sí. Todo queda en tu ordenador. Nada se envía a ningún servidor.

**¿Cuánto espacio necesita?**  
~5 GB en total (4.1 GB del modelo + ~900 MB de la app).

**¿En qué ordenadores funciona?**  
- macOS 11+ (Intel o Apple Silicon)  
- Windows 10/11 (64-bit)  
- Recomendado: 8 GB RAM mínimo, 16 GB ideal

**La app tarda mucho en responder, ¿es normal?**  
Sí. La IA corre en tu CPU (sin GPU). Cada respuesta puede tardar 20-90 segundos según la velocidad de tu ordenador. Es normal.

**El modelo tarda mucho la primera vez que cargo la app**  
La primera respuesta siempre tarda más porque la IA carga el modelo en memoria. Las siguientes respuestas en la misma sesión son más rápidas.
