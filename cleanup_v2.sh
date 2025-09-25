#!/bin/bash

# Script para limpiar procesos de v0.2 específicamente
# Uso: ./cleanup_v2.sh

echo "🧹 Limpiando procesos de v0.2..."

# Función para matar procesos de forma segura
kill_v2_processes() {
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

# Limpiar procesos de v0.2
kill_v2_processes "backend.v0_2.stm.app" "STM v0.2"
kill_v2_processes "backend.v0_2.server.app" "Server v0.2"
kill_v2_processes "python.*app.py" "Python app.py"

# Verificar puertos específicos de v0.2
echo "🔍 Verificando puertos de v0.2..."
for port in 8100 8200; do
    if lsof -ti:$port >/dev/null 2>&1; then
        echo "⚠️  El puerto $port aún está en uso"
        echo "   Matando procesos en puerto $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
        sleep 1
    else
        echo "✅ El puerto $port está libre"
    fi
done

echo ""
echo "🎉 Limpieza de v0.2 completada!"
echo "💡 Ahora puedes iniciar los servicios con:"
echo "   ./start_stm_v2.sh"
echo "   ./start_server_v2.sh"
