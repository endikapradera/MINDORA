#!/bin/bash

# MINDORA Installation Script
# Compatible with macOS, Linux, and Windows (Git Bash)
# This script sets up MINDORA completely

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  MINDORA - Instalador Automático                         ║${NC}"
echo -e "${BLUE}║  IA Educativa Offline - Setup Completamente Automatizado  ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

# Detectar SO
OS_TYPE=$(uname -s)
if [[ "$OS_TYPE" == "Darwin" ]]; then
  OS_NAME="macOS"
elif [[ "$OS_TYPE" == "Linux" ]]; then
  OS_NAME="Linux"
elif [[ "$OS_TYPE" == "MINGW64"* ]] || [[ "$OS_TYPE" == "MSYS"* ]]; then
  OS_NAME="Windows"
else
  OS_NAME="Unknown"
fi

echo -e "\n${BLUE}ℹ Sistema Operativo detectado: ${GREEN}$OS_NAME${NC}"

# 1. Verificar Python
echo -e "\n${BLUE}1️⃣  Verificando Python...${NC}"
if command -v python3 &> /dev/null; then
  PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  echo -e "${GREEN}✓ Python3 encontrado: $PYTHON_VERSION${NC}"
else
  echo -e "${RED}✗ Python3 no instalado${NC}"
  echo "  Instala Python 3.9+ desde: https://www.python.org/downloads/"
  exit 1
fi

# 2. Verificar Node.js
echo -e "\n${BLUE}2️⃣  Verificando Node.js...${NC}"
if command -v node &> /dev/null; then
  NODE_VERSION=$(node --version)
  NPM_VERSION=$(npm --version)
  echo -e "${GREEN}✓ Node.js encontrado: $NODE_VERSION (npm: $NPM_VERSION)${NC}"
else
  echo -e "${RED}✗ Node.js no instalado${NC}"
  echo "  Instala Node.js 16+ desde: https://nodejs.org/"
  exit 1
fi

# 3. Verificar git
echo -e "\n${BLUE}3️⃣  Verificando Git...${NC}"
if command -v git &> /dev/null; then
  GIT_VERSION=$(git --version | awk '{print $3}')
  echo -e "${GREEN}✓ Git encontrado: $GIT_VERSION${NC}"
else
  echo -e "${RED}✗ Git no instalado${NC}"
  echo "  Instala Git desde: https://git-scm.com/downloads"
  exit 1
fi

# 4. Instalar dependencias Frontend
echo -e "\n${BLUE}4️⃣  Instalando dependencias Frontend (Vite + React)...${NC}"
cd "$(dirname "$0")/ui"
npm install
npm run build
echo -e "${GREEN}✓ Frontend compilado exitosamente${NC}"
cd - > /dev/null

# 5. Instalar dependencias Backend
echo -e "\n${BLUE}5️⃣  Instalando dependencias Backend (Python)...${NC}"
if [ -f "requirements.txt" ]; then
  pip3 install -r requirements.txt --quiet
  echo -e "${GREEN}✓ Dependencias Python instaladas${NC}"
else
  echo -e "${YELLOW}⚠ requirements.txt no encontrado, instalando dependencias manuales...${NC}"
  pip3 install fastapi uvicorn requests llama-cpp-python --quiet 2>/dev/null || true
fi

# 6. Crear directorio de modelos
echo -e "\n${BLUE}6️⃣  Preparando directorio de modelos...${NC}"
if [[ "$OS_NAME" == "macOS" ]]; then
  MODELS_DIR="$HOME/Documents/MINDORA/models"
elif [[ "$OS_NAME" == "Windows" ]]; then
  MODELS_DIR="$APPDATA/MINDORA/models"
else
  MODELS_DIR="$HOME/.local/share/MINDORA/models"
fi

mkdir -p "$MODELS_DIR"
echo -e "${GREEN}✓ Directorio de modelos: $MODELS_DIR${NC}"

# 7. Descargar modelos (si no existen)
echo -e "\n${BLUE}7️⃣  Verificando modelos GGUF...${NC}"
if [ ! -f "$MODELS_DIR/Qwen2.5-7B-Instruct-Q4_K_M.gguf" ]; then
  echo -e "${YELLOW}⚠ Qwen modelo no encontrado${NC}"
  echo "  Puedes descargarlo manualmente desde:"
  echo "  https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF"
  echo "  Y colocarlo en: $MODELS_DIR/"
else
  QWEN_SIZE=$(du -h "$MODELS_DIR/Qwen2.5-7B-Instruct-Q4_K_M.gguf" | awk '{print $1}')
  echo -e "${GREEN}✓ Qwen modelo presente: $QWEN_SIZE${NC}"
fi

if [ ! -f "$MODELS_DIR/devstralQ4_K_M.gguf" ]; then
  echo -e "${YELLOW}⚠ Devstral modelo no encontrado${NC}"
  echo "  Puedes descargarlo manualmente desde:"
  echo "  https://huggingface.co/mistralai/Devstral-Small-2505_gguf"
  echo "  Y colocarlo en: $MODELS_DIR/"
else
  DEVSTRAL_SIZE=$(du -h "$MODELS_DIR/devstralQ4_K_M.gguf" | awk '{print $1}')
  echo -e "${GREEN}✓ Devstral modelo presente: $DEVSTRAL_SIZE${NC}"
fi

# 8. Verificar documentación
echo -e "\n${BLUE}8️⃣  Verificando documentación...${NC}"
DOCS=("README_COMPLETO.md" "QUICK_START.md" "TEST_REPORT.md")
for doc in "${DOCS[@]}"; do
  if [ -f "$doc" ]; then
    echo -e "${GREEN}✓ $doc${NC}"
  fi
done

# 9. Tests
echo -e "\n${BLUE}9️⃣  ¿Ejecutar tests automáticos? (requiere modelos descargados)${NC}"
read -p "  Escribe 'si' para ejecutar tests, o presiona Enter para saltar: " run_tests

if [ "$run_tests" = "si" ] || [ "$run_tests" = "yes" ]; then
  echo -e "${BLUE}Iniciando servidor backend...${NC}"
  python3 core/run_server.py > /tmp/mindora_install_test.log 2>&1 &
  BACKEND_PID=$!
  sleep 10
  
  if kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Backend iniciado (PID: $BACKEND_PID)${NC}"
    
    echo -e "${BLUE}Ejecutando suite de tests...${NC}"
    if python3 core/test_temario_qa.py 2>&1 | grep -q "30/30 tests"; then
      echo -e "${GREEN}✓ Tests: 30/30 pasados (100%)${NC}"
    else
      echo -e "${YELLOW}⚠ Tests completados, revisa los resultados arriba${NC}"
    fi
    
    kill $BACKEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
  else
    echo -e "${RED}✗ Backend falló al iniciar${NC}"
    tail -20 /tmp/mindora_install_test.log
  fi
fi

# Final summary
echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           ✅ INSTALACIÓN COMPLETADA                        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${GREEN}MINDORA está listo para usar:${NC}\n"

echo -e "${YELLOW}1. Iniciar servidor:${NC}"
echo "   python3 core/run_server.py"

echo -e "\n${YELLOW}2. En otra terminal - ejecutar tests:${NC}"
echo "   python3 core/test_temario_qa.py"

echo -e "\n${YELLOW}3. Hacer preguntas:${NC}"
echo "   curl -X POST http://127.0.0.1:8000/api/ask \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"question\":\"¿Qué es IA?\",\"response_style\":\"corta\"}' \\"
echo "     -G -d 'branch=principal'"

echo -e "\n${YELLOW}📚 Para más información:${NC}"
echo "   • Guía rápida: QUICK_START.md"
echo "   • Documentación completa: README_COMPLETO.md"
echo "   • Resultados de tests: TEST_REPORT.md"

echo -e "\n${YELLOW}🔗 Repositorio:${NC}"
echo "   https://github.com/endikapradera/MINDORA"

echo ""
