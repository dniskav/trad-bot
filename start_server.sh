#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}🚀 Script para iniciar el servidor SIN entorno virtual${NC}"
    echo "----------------------------------------"
    echo "Uso: $0 [opción]"
    echo ""
    echo "Opciones:"
    echo "  --foreground    Ejecutar en primer plano"
    echo "  --background    Ejecutar en segundo plano"
    echo "  --stop          Detener servidor"
    echo "  --restart       Reiniciar servidor"
    echo "  --logs          Mostrar logs"
    echo "  --help          Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 --foreground    # Ejecutar en primer plano"
    echo "  $0 --background    # Ejecutar en segundo plano"
    echo "  $0 --stop          # Detener servidor"
    echo "  $0 --logs          # Ver logs"
}

# Función para verificar si el servidor está corriendo
is_server_running() {
    local port=${SERVER_V2_PORT:-8200}
    lsof -ti:"$port" >/dev/null 2>&1
}

# Función para detener el servidor
stop_server() {
    echo -e "${YELLOW}🛑 Deteniendo servidor...${NC}"
    
    if is_server_running; then
        pkill -f "backend/server.py"
        sleep 2
        
        if is_server_running; then
            echo -e "${RED}❌ No se pudo detener el servidor${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ Servidor detenido correctamente${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  El servidor no está corriendo${NC}"
    fi
}

# Función para ejecutar en primer plano
run_foreground() {
    echo -e "${BLUE}🚀 Iniciando servidor en primer plano (SIN venv)...${NC}"
    echo -e "${YELLOW}💡 Presiona Ctrl+C para detener${NC}"
    echo "----------------------------------------"
    
    # Limpiar procesos Python huérfanos antes de iniciar
    if [ -f "cleanup_python_processes.sh" ]; then
        echo -e "${YELLOW}🧹 Limpiando procesos Python huérfanos...${NC}"
        ./cleanup_python_processes.sh
        echo "----------------------------------------"
    fi
    
    cd backend
    # arrancar STM si no está en su puerto
    STM_PORT=${STM_PORT:-8100} ./start_stm.sh &
    # arrancar server v2 en su puerto
    SERVER_V2_PORT=${SERVER_V2_PORT:-8200} ./start_server_v2.sh
}

# Función para ejecutar en segundo plano
run_background() {
    echo -e "${BLUE}🚀 Iniciando servidor en segundo plano (SIN venv)...${NC}"
    
    # Limpiar procesos Python huérfanos antes de iniciar
    if [ -f "cleanup_python_processes.sh" ]; then
        echo -e "${YELLOW}🧹 Limpiando procesos Python huérfanos...${NC}"
        ./cleanup_python_processes.sh
    fi
    
    cd backend
    nohup STM_PORT=${STM_PORT:-8100} ./start_stm.sh > stm.log 2>&1 &
    STM_PID=$!
    nohup SERVER_V2_PORT=${SERVER_V2_PORT:-8200} ./start_server_v2.sh > server_v2.log 2>&1 &
    SERVER_PID=$!
    
    sleep 3
    
    if is_server_running; then
        echo -e "${GREEN}✅ Servidor iniciado correctamente${NC}"
        echo -e "${BLUE}📊 PID: $SERVER_PID${NC}"
        echo -e "${BLUE}📋 Logs STM: backend/stm.log${NC}"
        echo -e "${BLUE}📋 Logs Server v0.2: backend/server_v2.log${NC}"
        echo -e "${YELLOW}💡 Para detener: $0 --stop${NC}"
        echo -e "${YELLOW}💡 Para ver logs: $0 --logs${NC}"
    else
        echo -e "${RED}❌ Error: No se pudo iniciar el servidor${NC}"
        exit 1
    fi
}

# Función para mostrar logs
show_logs() {
    echo -e "${BLUE}📋 Mostrando logs:${NC}"
    echo "----------------------------------------"
    if [ -f "backend/server_v2.log" ]; then
        echo "--- Server v0.2 ---"; tail -50 backend/server_v2.log
    else
        echo -e "${YELLOW}⚠️  No se encontró el archivo de logs${NC}"
    fi
    if [ -f "backend/stm.log" ]; then
        echo "--- STM ---"; tail -50 backend/stm.log
    fi
    echo "----------------------------------------"
    echo -e "${YELLOW}💡 Para ver logs en tiempo real: tail -f backend/server.log${NC}"
}

# Función para reiniciar
restart_server() {
    echo -e "${BLUE}🔄 Reiniciando servidor...${NC}"
    stop_server
    sleep 2
    run_background
}

# Opción por defecto: foreground
ARG=${1:---foreground}

case "$ARG" in
    --foreground)
        run_foreground
        ;;
    --background)
        run_background
        ;;
    --stop)
        stop_server
        ;;
    --restart)
        restart_server
        ;;
    --logs)
        show_logs
        ;;
    --help)
        show_help
        ;;
    *)
        echo -e "${YELLOW}⚠️  Opción desconocida: $ARG. Ejecutando foreground por defecto...${NC}"
        run_foreground
        ;;
esac
