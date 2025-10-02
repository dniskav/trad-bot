#!/bin/bash

# Script para terminar procesos del trading bot de manera rápida
# Uso: ./kill_processes.sh [all|server|stm]

# Colores para output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Función para mostrar ayuda
show_help() {
    echo -e "${YELLOW}📋 Uso del script:${NC}"
    echo -e "  ${GREEN}./kill_processes.sh${NC}          # Muestra procesos corriendo"
    echo -e "  ${GREEN}./kill_processes.sh server${NC}    # Termina solo el servidor"
    echo -e "  ${GREEN}./kill_processes.sh stm${NC}       # Termina solo el STM"
    echo -e "  ${GREEN}./kill_processes.sh all${NC}       # Termina todos los procesos"
    echo ""
}

# Función para mostrar procesos corriendo
show_processes() {
    echo -e "${YELLOW}🔍 Procesos corriendo del trading bot:${NC}"
    echo "----------------------------------------"
    
    # Mostrar procesos del servidor
    SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
    if [ ! -z "$SERVER_PIDS" ]; then
        echo -e "🖥️  ${GREEN}Servidor (Puerto 8200):${NC}"
        ps -p $SERVER_PIDS -o pid,ppid,etime,command 2>/dev/null || true
        echo ""
    fi
    
    # Mostrar procesos del STM
    STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
    if [ ! -z "$STM_PIDS" ]; then
        echo -e "💹 ${GREEN}STM (Puerto 8100):${NC}"
        ps -p $STM_PIDS -o pid,ppid,etime,command 2>/dev/null || true
        echo ""
    fi
    
    # Si no hay procesos
    if [ -z "$SERVER_PIDS" ] && [ -z "$STM_PIDS" ]; then
        echo -e "${GREEN}✅ No hay procesos del trading bot corriendo${NC}"
    fi
}

# Función para terminar el servidor
kill_server() {
    echo -e "${YELLOW}🖥️  Terminando proceso del servidor...${NC}"
    
    SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
    if [ ! -z "$SERVER_PIDS" ]; then
        echo -e "${YELLOW}🔪 Enviando SIGTERM a PIDs: $SERVER_PIDS${NC}"
        kill -TERM $SERVER_PIDS 2>/dev/null || true
        sleep 2
        
        # Verificar si aún están corriendo
        SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
        if [ ! -z "$SERVER_PIDS" ]; then
            echo -e "${RED}⚡ Forzando terminación con SIGKILL: $SERVER_PIDS${NC}"
            kill -9 $SERVER_PIDS 2>/dev/null || true
            sleep 1
        fi
        
        # Verificación final
        SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
        if [ -z "$SERVER_PIDS" ]; then
            echo -e "${GREEN}✅ Servidor terminado correctamente${NC}"
        else
            echo -e "${RED}❌ Falló al terminar el servidor${NC}"
        fi
    else
        echo -e "${GREEN}✅ No hay procesos del servidor corriendo${NC}"
    fi
}

# Función para terminar el STM
kill_stm() {
    echo -e "${YELLOW}💹 Terminando proceso del STM...${NC}"
    
    STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
    if [ ! -z "$STM_PIDS" ]; then
        echo -e "${YELLOW}🔪 Enviando SIGTERM a PIDs: $STM_PIDS${NC}"
        kill -TERM $STM_PIDS 2>/dev/null || true
        sleep 2
        
        # Verificar si aún están corriendo
        STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
        if [ ! -z "$STM_PIDS" ]; then
            echo -e "${RED}⚡ Forzando terminación con SIGKILL: $STM_PIDS${NC}"
            kill -9 $STM_PIDS 2>/dev/null || true
            sleep 1
        fi
        
        # Verificación final
        STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
        if [ -z "$STM_PIDS" ]; then
            echo -e "${GREEN}✅ STM terminado correctamente${NC}"
        else
            echo -e "${RED}❌ Falló al terminar el STM${NC}"
        fi


    else
        echo -e "${GREEN}✅ No hay procesos del STM corriendo${NC}"
    fi
}

# Función para terminar todos los procesos
kill_all() {
    echo -e "${YELLOW}🔥 Terminando todos los procesos del trading bot...${NC}"
    
    # Usar pkill para mayor eficiencia
    echo -e "${YELLOW}🔸 Terminando servidor...${NC}"
    pkill -f "backend.v0_2.server.app" 2>/dev/null || true
    
    echo -e "${YELLOW}🔸 Terminando STM...${NC}"
    pkill -f "backend.v0_2.stm.app" 2>/dev/null || true
    
    sleep 3
    
    # Verificar si quedaron procesos
    REMAINING=$(pgrep -u "$USER" -f "backend.v0_2.*app" 2>/dev/null || true)
    if [ ! -z "$REMAINING" ]; then
        echo -e "${RED}⚡ Procesos persistentes: $REMAINING - Forzando terminación...${NC}"
        echo $REMAINING | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Verificación final
    REMAINING=$(pgrep -u "$USER" -f "backend.v0_2.*app" 2>/dev/null || true)
    if [ -z "$REMAINING" ]; then
        echo -e "${GREEN}✅ Todos los procesos terminados correctamente${NC}"
    else
        echo -e "${RED}❌ Aún quedan procesos: $REMAINING${NC}"
    fi
}

# Verificar puertos después de terminar
check_ports() {
    echo ""
    echo -e "${YELLOW}🔍 Verificando puertos...${NC}"
    
    if lsof -i :8200 >/dev/null 2>&1; then
        echo -e "${RED}⚠️  Puerto 8200 aún ocupado${NC}"
        lsof -i :8200
    else
        echo -e "${GREEN}✅ Puerto 8200 libre${NC}"
    fi
    
    if lsof -i :8100 >/dev/null 2>&1; then
        echo -e "${RED}⚠️  Puerto 8100 aún ocupado${NC}"
        lsof -i :8100
    else
        echo -e "${GREEN}✅ Puerto 8100 libre${NC}"
    fi
}

# Main script
case "${1:-show}" in
    "show"|"")
        show_processes
        ;;
    "server")
        kill_server
        check_ports
        ;;
    "stm")
        kill_stm
        check_ports
        ;;
    "all")
        kill_all
        check_ports
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Opción inválida: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
