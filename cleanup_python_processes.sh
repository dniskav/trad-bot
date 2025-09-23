#!/bin/bash

# Script de limpieza de procesos Python huérfanos
# Uso: ./cleanup_python_processes.sh

echo "🧹 Limpiando procesos Python huérfanos..."

# Función para matar procesos de forma segura
kill_processes() {
    local pattern="$1"
    local description="$2"
    
    if pgrep -f "$pattern" > /dev/null; then
        echo "🔍 Encontrados procesos de $description:"
        pgrep -f "$pattern" | while read pid; do
            echo "   PID: $pid"
        done
        
        echo "💀 Matando procesos de $description..."
        pkill -f "$pattern"
        sleep 1
        
        # Verificar si aún existen
        if pgrep -f "$pattern" > /dev/null; then
            echo "⚠️  Algunos procesos aún existen, forzando terminación..."
            pkill -9 -f "$pattern"
            sleep 1
        fi
        
        if ! pgrep -f "$pattern" > /dev/null; then
            echo "✅ Procesos de $description eliminados"
        else
            echo "❌ No se pudieron eliminar todos los procesos de $description"
        fi
    else
        echo "✅ No se encontraron procesos de $description"
    fi
    echo ""
}

# Limpiar procesos de multiprocessing
kill_processes "spawn_main" "multiprocessing spawn_main"
kill_processes "resource_tracker" "multiprocessing resource_tracker"
kill_processes "multiprocessing" "multiprocessing general"

# Limpiar procesos de trading
kill_processes "trading_tracker" "trading tracker"
kill_processes "server_simple" "servidor simple"
kill_processes "aggressive_scalping_bot" "bot agresivo"
kill_processes "sma_cross_bot" "bot SMA cross"
kill_processes "conservative_scalping_bot" "bot conservador"

# Limpiar otros procesos Python relacionados
kill_processes "python.*trading" "Python trading"
kill_processes "python.*bot" "Python bots"

# Verificar procesos Python restantes
echo "🔍 Verificando procesos Python restantes..."
remaining_processes=$(pgrep -f "python" | wc -l)
if [ "$remaining_processes" -gt 0 ]; then
    echo "⚠️  Aún hay $remaining_processes procesos Python en ejecución:"
    pgrep -f "python" | while read pid; do
        echo "   PID: $pid - $(ps -p $pid -o comm= 2>/dev/null || echo 'Proceso no encontrado')"
    done
else
    echo "✅ No hay procesos Python en ejecución"
fi

echo ""
echo "🎉 Limpieza completada!"
echo "💡 Ahora puedes iniciar el servidor de forma segura"
