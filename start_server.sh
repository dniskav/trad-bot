#!/bin/bash

# Script para iniciar el servidor de trading bot
# Uso: ./start_server.sh [opciones]

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo -e "${BLUE}Trading Bot Server Launcher${NC}"
    echo ""
    echo "Uso: $0 [opciones]"
    echo ""
    echo "Opciones:"
    echo "  -h, --help     Mostrar esta ayuda"
    echo "  -b, --background  Ejecutar en segundo plano (nohup)"
    echo "  -f, --foreground  Ejecutar en primer plano (terminal visible)"
    echo "  -s, --stop     Detener el servidor si está corriendo"
    echo "  -r, --restart  Reiniciar el servidor"
    echo "  -l, --logs     Mostrar logs del servidor"
    echo ""
    echo "Ejemplos:"
    echo "  $0                    # Ejecutar en primer plano"
    echo "  $0 --background       # Ejecutar en segundo plano"
    echo "  $0 --stop             # Detener servidor"
    echo "  $0 --restart          # Reiniciar servidor"
    echo "  $0 --logs             # Ver logs"
}

# Función para verificar si el servidor está corriendo
is_server_running() {
    pgrep -f "server_simple.py" > /dev/null 2>&1
}

# Función para detener el servidor
stop_server() {
    echo -e "${YELLOW}🛑 Deteniendo servidor...${NC}"
    
    if is_server_running; then
        pkill -f "server_simple.py"
        sleep 2
        
        # Forzar detención si aún está corriendo
        if is_server_running; then
            pkill -9 -f "server_simple.py"
            sleep 1
        fi
        
        if is_server_running; then
            echo -e "${RED}❌ Error: No se pudo detener el servidor${NC}"
            exit 1
        else
            echo -e "${GREEN}✅ Servidor detenido correctamente${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  El servidor no está corriendo${NC}"
    fi
}

# Función para mostrar logs
show_logs() {
    if [ -f "backend/server.log" ]; then
        echo -e "${BLUE}📋 Mostrando logs del servidor:${NC}"
        echo "----------------------------------------"
        tail -50 backend/server.log
        echo "----------------------------------------"
        echo -e "${YELLOW}💡 Para ver logs en tiempo real: tail -f backend/server.log${NC}"
    else
        echo -e "${RED}❌ No se encontró el archivo de logs${NC}"
    fi
}

# Función para ejecutar en primer plano
run_foreground() {
    echo -e "${BLUE}🚀 Iniciando servidor en primer plano...${NC}"
    echo -e "${YELLOW}💡 Presiona Ctrl+C para detener${NC}"
    echo "----------------------------------------"
    
    # Limpiar procesos Python huérfanos antes de iniciar
    if [ -f "cleanup_python_processes.sh" ]; then
        echo -e "${YELLOW}🧹 Limpiando procesos Python huérfanos...${NC}"
        ./cleanup_python_processes.sh
        echo "----------------------------------------"
    fi
    
    # Activar entorno virtual
    if [ -f ".venv/bin/activate" ]; then
        echo -e "${GREEN}✅ Activando entorno virtual...${NC}"
        source .venv/bin/activate
    else
        echo -e "${YELLOW}⚠️  No se encontró entorno virtual, usando Python del sistema${NC}"
    fi
    
    cd backend
    python3 server_simple.py
}

# Función para ejecutar en segundo plano
run_background() {
    echo -e "${BLUE}🚀 Iniciando servidor en segundo plano...${NC}"
    
    # Limpiar procesos Python huérfanos antes de iniciar
    if [ -f "cleanup_python_processes.sh" ]; then
        echo -e "${YELLOW}🧹 Limpiando procesos Python huérfanos...${NC}"
        ./cleanup_python_processes.sh
    fi
    
    # Activar entorno virtual
    if [ -f ".venv/bin/activate" ]; then
        echo -e "${GREEN}✅ Activando entorno virtual...${NC}"
        source .venv/bin/activate
    else
        echo -e "${YELLOW}⚠️  No se encontró entorno virtual, usando Python del sistema${NC}"
    fi
    
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

# Función para reiniciar
restart_server() {
    echo -e "${BLUE}🔄 Reiniciando servidor...${NC}"
    stop_server
    sleep 2
    run_background
}

# Verificar que estamos en el directorio correcto
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: No se encontró la carpeta 'backend'${NC}"
    echo -e "${YELLOW}💡 Asegúrate de ejecutar este script desde la raíz del proyecto${NC}"
    exit 1
fi

# Verificar que Python está disponible
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python3 no está instalado o no está en el PATH${NC}"
    exit 1
fi

# Verificar que el archivo del servidor existe
if [ ! -f "backend/server_simple.py" ]; then
    echo -e "${RED}❌ Error: No se encontró backend/server_simple.py${NC}"
    exit 1
fi

# Procesar argumentos
case "${1:-}" in
    -h|--help)
        show_help
        ;;
    -b|--background)
        if is_server_running; then
            echo -e "${YELLOW}⚠️  El servidor ya está corriendo${NC}"
            echo -e "${YELLOW}💡 Usa '$0 --restart' para reiniciar${NC}"
        else
            run_background
        fi
        ;;
    -f|--foreground)
        if is_server_running; then
            echo -e "${YELLOW}⚠️  El servidor ya está corriendo${NC}"
            echo -e "${YELLOW}💡 Usa '$0 --stop' para detener primero${NC}"
        else
            run_foreground
        fi
        ;;
    -s|--stop)
        stop_server
        ;;
    -r|--restart)
        restart_server
        ;;
    -l|--logs)
        show_logs
        ;;
    "")
        # Sin argumentos, ejecutar en primer plano por defecto
        if is_server_running; then
            echo -e "${YELLOW}⚠️  El servidor ya está corriendo${NC}"
            echo -e "${YELLOW}💡 Usa '$0 --stop' para detener o '$0 --restart' para reiniciar${NC}"
        else
            run_foreground
        fi
        ;;
    *)
        echo -e "${RED}❌ Opción desconocida: $1${NC}"
        echo -e "${YELLOW}💡 Usa '$0 --help' para ver las opciones disponibles${NC}"
        exit 1
        ;;
esac
