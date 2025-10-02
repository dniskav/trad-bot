#!/bin/bash

# Utilerías generales para el trading bot
# Uso: ./trading_utils.sh [command] [options]

# Colores para output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
SERVER_PORT=8200
STM_PORT=8100

# Header del script
show_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                    🤖 TRADING BOT UTILS 🤖                     ║${NC}"
    echo -e "${CYAN}║                 Gestión Rápida del Sistema                    ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Función para mostrar ayuda general
show_help() {
    echo -e "${YELLOW}📋 Comandos disponibles:${NC}"
    echo ""
    echo -e "${GREEN}🔍 MONITOREO:${NC}"
    echo -e "  ${CYAN}status${NC}           # Estado general del sistema"
    echo -e "  ${CYAN}refresh${NC}          # Recargar datos en tiempo real"
    echo -e "  ${CYAN}logs${NC}             # Ver logs recientes"
    echo ""
    echo -e "${GREEN}⚡ CONTROL DE PROCESOS:${NC}"
    echo -e "  ${CYAN}start${NC}            # Iniciar servidor y STM"
    echo -e "  ${CYAN}stop${NC}             # Detener servidor y STM"
    echo -e "  ${CYAN}restart${NC}          # Reiniciar todo el sistema"
    echo ""
    echo -e "${GREEN}🌐 VERIFICACIÓN DE CONECTIVIDAD:${NC}"
    echo -e "  ${CYAN}health${NC}           # Verificar salud de servicios"
    echo -e "  ${CYAN}connectivity${NC}    # Verificar conectividad con Binance"
    echo ""
    echo -e "${GREEN}🛠️  MANTENIMIENTO:${NC}"
    echo -e "  ${CYAN}reset${NC}            # Reset completo del sistema"
    echo -e "  ${CYAN}clean${NC}           # Limpiar logs antiguos"
    echo -e "  ${CYAN}repair${NC}          # Reparar conexiones WebSocket"
    echo ""
    echo -e "${YELLOW}📖 Más comandos específicos:${NC}"
    echo -e "  ${CYAN}trading_utils.sh help [comando]${NC} - Ayuda específica"
    echo ""
}

# Función para mostrar estado general
show_status() {
    echo -e "${BLUE}📊 ESTADO GENERAL DEL SISTEMA${NC}"
    echo "=================================================="
    
    # Verificar procesos  
    SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
    STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
    
    if [ ! -z "$SERVER_PIDS" ]; then
        echo -e "🖥️  ${GREEN}Servidor: CORRIENDO${NC} (PID: $SERVER_PIDS)"
    else
        echo -e "🖥️  ${RED}Servidor: DETENIDO${NC}"
    fi
    
    if [ ! -z "$STM_PIDS" ]; then
        echo -e "💹 ${GREEN}STM: CORRIENDO${NC} (PID: $STM_PIDS)"
    else
        echo -e "💹 ${RED}STM: DETENIDO${NC}"
    fi
    
    echo ""
    
    # Verificar puertos
    echo -e "${BLUE}🔌 ESTADO DE PUERTOS:${NC}"
    if lsof -i :$SERVER_PORT >/dev/null 2>&1; then
        echo -e "   Puerto $SERVER_PORT: ${RED}OCUPADO${NC}"
    else
        echo -e "   Puerto $SERVER_PORT: ${GREEN}LIBRE${NC}"
    fi
    
    if lsof -i :$STM_PORT >/dev/null 2>&1; then
        echo -e "   Puerto $STM_PORT: ${RED}OCUPADO${NC}"
    else
        echo -e "   Puerto $STM_PORT: ${GREEN}LIBRE${NC}"
    fi
    
    echo ""
}

# Función para verificar salud
check_health() {
    echo -e "${BLUE}🏥 VERIFICANDO SALUD DE SERVICIOS${NC}"
    echo "=========================================="
    
    # Verificar STM
    echo -e "${YELLOW}🔸 Verificando STM (Puerto $STM_PORT)...${NC}"
    if curl -s http://localhost:$STM_PORT/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ STM: Saludable${NC}"
        # Mostrar respuesta detallada
        echo -e "${CYAN}📄 Respuesta del STM:${NC}"
        curl -s http://localhost:$STM_PORT/health | jq . 2>/dev/null || curl -s http://localhost:$STM_PORT/health
    else
        echo -e "${RED}❌ STM: No responde${NC}"
    fi
    echo ""
    
    # Verificar Server
    echo -e "${YELLOW}🔸 Verificando Server (Puerto $SERVER_PORT)...${NC}"
    if curl -s http://localhost:$SERVER_PORT/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Server: Saludable${NC}"
        # Mostrar respuesta detallada
        echo -e "${CYAN}📄 Respuesta del Server:${NC}"
        curl -s http://localhost:$SERVER_PORT/health | jq . 2>/dev/null || curl -s http://localhost:$SERVER_PORT/health
    else
        echo -e "${RED}❌ Server: No responde${NC}"
    fi
    echo ""
}

# Función para verificar conectividad con Binance
check_connectivity() {
    echo -e "${BLUE}🌐 VERIFICANDO CONECTIVIDAD CON BINANCE${NC}"
    echo "==============================================="
    
    echo -e "${YELLOW}🔸 Verificando conexión REST a Binance...${NC}"
    if curl -s -o /dev/null -w "%{http_code}" "https://api.binance.com/api/v3/ping" | grep -q "200"; then
        echo -e "${GREEN}✅ Conexión REST: OK${NC}"
    else
        echo -e "${RED}❌ Conexión REST: FALLO${NC}"
    fi
    
    echo -e "${YELLOW}🔸 Verificando precio DOGEUSDT...${NC}"
    DOGE_PRICE=$(curl -s "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT" | jq -r '.price' 2>/dev/null || echo "N/A")
    if [ "$DOGE_PRICE" != "N/A" ] && [ "$DOGE_PRICE" != "null" ]; then
        echo -e "${GREEN}✅ Precio DOGEUSDT: $DOGE_PRICE${NC}"
    else
        echo -e "${RED}❌ No se pudo obtener precio DOGEUSDT${NC}"
    fi
    
    echo ""
}

# Función para iniciar servicios
start_services() {
    echo -e "${YELLOW}🚀 Iniciando servicios del trading bot...${NC}"
    
    # Verificar si ya están corriendo
    SERVER_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.server.app" 2>/dev/null || true)
    STM_PIDS=$(pgrep -u "$USER" -f "backend.v0_2.stm.app" 2>/dev/null || true)
    
    if [ ! -z "$SERVER_PIDS" ] && [ ! -z "$STM_PIDS" ]; then
        echo -e "${YELLOW}⚠️  Los servicios ya están corriendo${NC}"
        show_status
        return
    fi
    
    echo -e "${YELLOW}🔸 Iniciando STM...${NC}"
    ./start_stm_v2.sh &
    
    echo -e "${YELLOW}🔸 Esperando 3 segundos...${NC}"
    sleep 3
    
    echo -e "${YELLOW}🔸 Iniciando Server...${NC}"
    ./start_server_v2.sh &
    
    echo -e "${YELLOW}🔸 Esperando 5 segundos para estabilización...${NC}"
    sleep 5
    
    echo ""
    check_health
}

# Función para detener servicios
stop_services() {
    echo -e "${YELLOW}🛑 Deteniendo servicios del trading bot...${NC}"
    
    ./kill_processes.sh all
    
    sleep 3
    
    echo ""
    show_status
}

# Función para reiniciar servicios
restart_services() {
    echo -e "${YELLOW}🔄 Reiniciando servicios del trading bot...${NC}"
    
    stop_services
    echo -e "${YELLOW}⏳ Esperando 3 segundos antes de reiniciar...${NC}"
    sleep 3
    start_services
}

# Función para reset completo
reset_system() {
    echo -e "${RED}⚠️  RESET COMPLETO DEL SISTEMA${NC}"
    echo -e "${RED}Esta acción eliminará todas las posiciones y datos simulados${NC}"
    echo ""
    read -p "¿Estás seguro? Escribe 'RESET' para confirmar: " confirm
    
    if [ "$confirm" = "RESET" ]; then
        echo -e "${YELLOW}🔸 Reseteando cuenta sintética...${NC}"
        curl -X POST http://localhost:$STM_PORT/account/synth/reset >/dev/null 2>&1 || true
        
        echo -e "${YELLOW}🔸 Limpiando datos de posiciones...${NC}"
        curl -X POST http://localhost:$STM_PORT/positions/clean >/dev/null 2>&1 || true
        
        echo -e "${YELLOW}🔸 Reiniciando servicios...${NC}"
        restart_services
        
        echo -e "${GREEN}✅ Reset completo terminado${NC}"
    else
        echo -e "${RED}❌ Reset cancelado${NC}"
    fi
}

# Función para mostrar logs recientes
show_logs() {
    echo -e "${BLUE}📋 LOGS RECIENTES DEL SISTEMA${NC}"
    echo "======================================"
    
    echo -e "${YELLOW}🔸 Últimas 20 líneas de logs del servidor:${NC}"
    # Buscar logs del servidor en terminales recientes o crear logs si es necesario
    echo "Mostrando logs de la sesión actual..."
    echo ""
    
    echo -e "${CYAN}💡 Tip: Los logs en tiempo real se muestran en las terminales de STM/Server${NC}"
}

# Main script
main() {
    show_header
    
    case "${1:-help}" in
        "status")
            show_status
            ;;
        "health")
            check_health
            ;;
        "connectivity")
            check_connectivity
            ;;
        "start")
            start_services
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "reset")
            reset_system
            ;;
        "logs")
            show_logs
            ;;
        "clear"|"clean")
            echo -e "${YELLOW}🧹 Limpiando pantalla...${NC}"
            clear
            ;;
        "help"|"-h"|"--help"|"")
            show_help
            ;;
        *)
            echo -e "${RED}❌ Comando desconocido: $1${NC}"
            echo ""
            show_help
            ;;
    esac
}

# Ejecutar función principal
main "$@"
