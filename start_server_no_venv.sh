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
    if pgrep -f "server_simple.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Función para detener el servidor
stop_server() {
    echo -e "${YELLOW}🛑 Deteniendo servidor...${NC}"
    
    if is_server_running; then
        pkill -f "server_simple.py"
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
    
    cd backend
    python3 server_simple.py
}

# Función para ejecutar en segundo plano
run_background() {
    echo -e "${BLUE}🚀 Iniciando servidor en segundo plano (SIN venv)...${NC}"
    
    cd backend
    nohup python3 server_simple.py > server.log 2>&1 &
    SERVER_PID=$!
    
    sleep 3
    
    if is_server_running; then
        echo -e "${GREEN}✅ Servidor iniciado correctamente${NC}"
        echo -e "${BLUE}📊 PID: $SERVER_PID${NC}"
        echo -e "${BLUE}📋 Logs: backend/server.log${NC}"
        echo -e "${YELLOW}💡 Para detener: $0 --stop${NC}"
        echo -e "${YELLOW}💡 Para ver logs: $0 --logs${NC}"
    else
        echo -e "${RED}❌ Error: No se pudo iniciar el servidor${NC}"
        exit 1
    fi
}

# Función para mostrar logs
show_logs() {
    echo -e "${BLUE}📋 Mostrando logs del servidor:${NC}"
    echo "----------------------------------------"
    if [ -f "backend/server.log" ]; then
        tail -50 backend/server.log
    else
        echo -e "${YELLOW}⚠️  No se encontró el archivo de logs${NC}"
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

# Verificar argumentos
case "$1" in
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
        echo -e "${RED}❌ Opción desconocida: $1${NC}"
        echo -e "${YELLOW}💡 Usa '$0 --help' para ver las opciones disponibles${NC}"
        exit 1
        ;;
esac
