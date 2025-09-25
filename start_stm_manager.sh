#!/bin/bash

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

STM_HEALTH="http://127.0.0.1:8100/health"

show_help() {
  echo -e "${BLUE}🚀 Script para iniciar el STM (Synth Trading Manager)${NC}"
  echo "----------------------------------------"
  echo "Uso: $0 [opción]"
  echo ""
  echo "Opciones:"
  echo "  --foreground    Ejecutar en primer plano"
  echo "  --background    Ejecutar en segundo plano"
  echo "  --stop          Detener STM"
  echo "  --restart       Reiniciar STM"
  echo "  --logs          Mostrar logs"
  echo "  --health        Consultar /health"
  echo "  --help          Mostrar esta ayuda"
}

is_stm_running() {
  pgrep -f "uvicorn.*backend.v0_2.stm.app" >/dev/null 2>&1
}

stop_stm() {
  echo -e "${YELLOW}🛑 Deteniendo STM...${NC}"
  pkill -f "uvicorn.*backend.v0_2.stm.app" 2>/dev/null || true
  sleep 1
  if is_stm_running; then
    echo -e "${RED}❌ No se pudo detener el STM${NC}"
    exit 1
  else
    echo -e "${GREEN}✅ STM detenido${NC}"
  fi
}

run_foreground() {
  echo -e "${BLUE}🚀 Iniciando STM en primer plano...${NC}"
  cd backend
  ./start_stm.sh
}

run_background() {
  echo -e "${BLUE}🚀 Iniciando STM en segundo plano...${NC}"
  cd backend
  nohup ./start_stm.sh > stm.log 2>&1 &
  sleep 2
  if is_stm_running; then
    echo -e "${GREEN}✅ STM iniciado${NC}"
    echo -e "${BLUE}📋 Logs: backend/stm.log${NC}"
  else
    echo -e "${RED}❌ Error iniciando STM${NC}"
    exit 1
  fi
}

show_logs() {
  echo -e "${BLUE}📋 Logs STM:${NC}"
  if [ -f "backend/stm.log" ]; then
    tail -50 backend/stm.log
  else
    echo -e "${YELLOW}⚠️  No se encontró backend/stm.log${NC}"
  fi
}

health() {
  echo -e "${BLUE}🔎 Consultando salud STM:${NC}"
  curl -s "$STM_HEALTH" || true
  echo ""
}

# Opción por defecto: foreground
ARG=${1:---foreground}

case "$ARG" in
  --foreground) run_foreground ;;
  --background) run_background ;;
  --stop)       stop_stm ;;
  --restart)    stop_stm; run_background ;;
  --logs)       show_logs ;;
  --health)     health ;;
  --help|*)     show_help ;;
esac


