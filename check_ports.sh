#!/bin/bash

# Script para verificar y gestionar puertos del trading bot
# Uso: ./check_ports.sh [check|free|free-all]

# Colores para output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PORT_SERVER=8200
PORT_STM=8100

# Función para mostrar ayuda
show_help() {
    echo -e "${YELLOW}📋 Uso del script check_ports.sh:${NC}"
    echo -e "  ${GREEN}./check_ports.sh${NC}         # Muestra estado de puertos"
    echo -e "  ${GREEN}./check_ports.sh check${NC}   # Verifica puertos (alias del comando anterior)"
    echo -e "  ${GREEN}./check_ports.sh free${NC}    # Libera puertos específicos"
    echo -e "  ${GREEN}./check_ports.sh free-all${NC} # Libera todos los puertos ocupados"
    echo -e "  ${GREEN}./check_ports.sh help${NC}     # Muestra esta ayuda"
    echo ""
}

# Función para verificar puertos
check_ports() {
    echo -e "${BLUE}🔍 Verificando puertos del trading bot...${NC}"
    echo "=========================================="
    
    # Verificar puerto del servidor (8200)
    if lsof -i :$PORT_SERVER >/dev/null 2>&1; then
        echo -e "${RED}🚫 Puerto $PORT_SERVER (Servidor) OCUPADO${NC}"
        echo -e "${YELLOW}📋 Procesos en puerto $PORT_SERVER:${NC}"
        lsof -i :$PORT_SERVER
    else
        echo -e "${GREEN}✅ Puerto $PORT_SERVER (Servidor) LIBRE${NC}"
    fi
    echo ""
    
    # Verificar puerto del STM (8100)
    if lsof -i :$PORT_STM >/dev/null 2>&1; then
        echo -e "${RED}🚫 Puerto $PORT_STM (STM) OCUPADO${NC}"
        echo -e "${YELLOW}📋 Procesos en puerto $PORT_STM:${NC}"
        lsof -i :$PORT_STM
    else
        echo -e "${GREEN}✅ Puerto $PORT_STM (STM) LIBRE${NC}"
    fi
    echo ""
    
    # Verificar otros puertos comunes
    OTHER_PORTS=(3000 5173 8080 8000 3001)
    echo -e "${BLUE}🔍 Otros puertos comunes:${NC}"
    for port in "${OTHER_PORTS[@]}"; do
        if lsof -i :$port >/dev/null 2>&1; then
            echo -e "${YELLOW}⚡ Puerto $port ocupado${NC}"
        else
            echo -e "${GREEN}✅ Puerto $port libre${NC}"
        fi
    done
}

# Función para liberar puertos específicos
free_ports() {
    echo -e "${YELLOW}🔧 Liberando puertos específicos del trading bot...${NC}"
    
    # Liberar puerto del servidor
    if lsof -i :$PORT_SERVER >/dev/null 2>&1; then
        echo -e "${YELLOW}🔪 Liberando puerto $PORT_SERVER...${NC}"
        PORT_PIDS=$(lsof -ti :$PORT_SERVER 2>/dev/null || true)
        if [ ! -z "$PORT_PIDS" ]; then
            echo -e "${YELLOW}⚡ Terminando procesos: $PORT_PIDS${NC}"
            echo $PORT_PIDS | xargs kill -TERM 2>/dev/null || true
            sleep 2
            
            # Verificar si aún persisten
            PORT_PIDS=$(lsof -ti :$PORT_SERVER 2>/dev/null || true)
            if [ ! -z "$PORT_PIDS" ]; then
                echo -e "${RED}💥 Forzando terminación: $PORT_PIDS${NC}"
                echo $PORT_PIDS | xargs kill -9 2>/dev/null || true
                sleep 1
            fi
        fi
    fi
    
    # Liberar puerto del STM
    if lsof -i :$PORT_STM >/dev/null 2>&1; then
        echo -e "${YELLOW}🔪 Liberando puerto $PORT_STM...${NC}"
        PORT_PIDS=$(lsof -ti :$PORT_STM 2>/dev/null || true)
        if [ ! -z "$PORT_PIDS" ]; then
            echo -e "${YELLOW}⚡ Terminando procesos: $PORT_PIDS${NC}"
            echo $PORT_PIDS | xargs kill -TERM 2>/dev/null || true
            sleep 2
            
            # Verificar si aún persisten
            PORT_PIDS=$(lsof -ti :$PORT_STM 2>/dev/null || true)
            if [ ! -z "$PORT_PIDS" ]; then
                echo -e "${RED}💥 Forzando terminación: $PORT_PIDS${NC}"
                echo $PORT_PIDS | xargs kill -9 2>/dev/null || true
                sleep 1
            fi
        fi
    fi
    
    echo -e "${BLUE}🔍 Verificando resultado...${NC}"
    check_ports
}

# Función para liberar todos los puertos ocupados por el trading bot
free_all() {
    echo -e "${YELLOW}🔥 Liberando todos los puertos ocupados por el trading bot...${NC}"
    
    # Terminar todos los procesos relacionados
    echo -e "${YELLOW}🔸 Terminando proceso servidor...${NC}"
    pkill -f "backend.v0_2.server.app" 2>/dev/null || true
    
    echo -e "${YELLOW}🔸 Terminando proceso STM...${NC}"
    pkill -f "backend.v0_2.stm.app" 2>/dev/null || true
    
    sleep 3
    
    # Liberar puertos manualmente si persisten
    echo -e "${YELLOW}🔧 Liberando puertos directamente...${NC}"
    lsof -ti :$PORT_SERVER | xargs kill -9 2>/dev/null || true
    lsof -ti :$PORT_STM | xargs kill -9 2>/dev/null || true
    
    sleep 1
    
    echo -e "${BLUE}🔍 Verificando resultado final...${NC}"
    check_ports
}

# Función para mostrar puertos utilizados por otros procesos
show_other_processes() {
    echo -e "${BLUE}🔍 Otros procesos corriendo (python/backend):${NC}"
    echo "=========================================="
    
    BACKEND_PROCESSES=$(ps aux | grep python | grep backend | grep -v grep || true)
    if [ ! -z "$BACKEND_PROCESSES" ]; then
        echo "$BACKEND_PROCESSES"
    else
        echo -e "${GREEN}✅ No hay otros procesos python/backend corriendo${NC}"
    fi
    echo ""
}

# Main script
case "${1:-check}" in
    "check"|"")
        check_ports
        echo ""
        show_other_processes
        ;;
    "free")
        free_ports
        ;;
    "free-all")
        free_all
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
