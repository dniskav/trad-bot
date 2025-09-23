#!/bin/bash

# Script para arreglar el error "Address already in use" en el puerto 8000
# Autor: Trading Bot Assistant
# Fecha: $(date)

echo "🔧 Arreglando error 'Address already in use' en puerto 8000..."

# Función para mostrar procesos en el puerto 8000
show_port_processes() {
    echo "📋 Procesos usando el puerto 8000:"
    lsof -ti:8000 | while read pid; do
        if [ ! -z "$pid" ]; then
            echo "  PID: $pid - $(ps -p $pid -o comm= 2>/dev/null || echo 'Proceso no encontrado')"
        fi
    done
}

# Función para matar procesos en el puerto 8000
kill_port_processes() {
    echo "🛑 Matando procesos en el puerto 8000..."
    pids=$(lsof -ti:8000)
    if [ ! -z "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ Procesos terminados"
    else
        echo "ℹ️  No hay procesos usando el puerto 8000"
    fi
}

# Función para matar procesos específicos del servidor
kill_server_processes() {
    echo "🛑 Matando procesos específicos del servidor..."
    
    # Matar procesos de uvicorn
    pkill -f "uvicorn.*server" 2>/dev/null
    pkill -f "python.*server.py" 2>/dev/null
    
    # Matar procesos de trading bot
    pkill -f "trading.*bot" 2>/dev/null
    pkill -f "real_trading_manager" 2>/dev/null
    pkill -f "trading_tracker" 2>/dev/null
    
    sleep 2
    echo "✅ Procesos del servidor terminados"
}

# Función para verificar si el puerto está libre
check_port_free() {
    if lsof -ti:8000 >/dev/null 2>&1; then
        echo "❌ El puerto 8000 aún está en uso"
        return 1
    else
        echo "✅ El puerto 8000 está libre"
        return 0
    fi
}

# Función para limpiar procesos Python huérfanos
cleanup_python_processes() {
    echo "🧹 Limpiando procesos Python huérfanos..."
    
    # Procesos de multiprocessing
    pkill -f "multiprocessing.spawn_main" 2>/dev/null
    pkill -f "multiprocessing.resource_tracker" 2>/dev/null
    
    # Procesos de trading
    pkill -f "trading.*tracker" 2>/dev/null
    pkill -f "bot.*agresivo" 2>/dev/null
    pkill -f "bot.*conservador" 2>/dev/null
    
    sleep 1
    echo "✅ Limpieza completada"
}

# Función principal
main() {
    echo "=========================================="
    echo "🔧 FIX PORT 8000 - Trading Bot"
    echo "=========================================="
    
    # Mostrar procesos actuales
    show_port_processes
    
    # Limpiar procesos Python huérfanos
    cleanup_python_processes
    
    # Matar procesos específicos del servidor
    kill_server_processes
    
    # Matar cualquier proceso en el puerto 8000
    kill_port_processes
    
    # Verificar que el puerto esté libre
    if check_port_free; then
        echo ""
        echo "🎉 ¡Puerto 8000 liberado exitosamente!"
        echo ""
        echo "💡 Ahora puedes iniciar el servidor con:"
        echo "   ./start_server.sh --start"
        echo "   o"
        echo "   ./start_server.sh --foreground"
        echo ""
    else
        echo ""
        echo "⚠️  El puerto 8000 aún está en uso. Intenta:"
        echo "   1. Reiniciar tu terminal"
        echo "   2. Ejecutar: sudo lsof -ti:8000 | xargs sudo kill -9"
        echo "   3. Reiniciar tu computadora si es necesario"
        echo ""
    fi
}

# Ejecutar función principal
main
