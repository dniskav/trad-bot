#!/bin/bash

# Script para iniciar Server v0.3
# Puerto<｜tool▁sep｜>content
#!/bin/bash

# Script para iniciar Server v0.3
# Puerto: 8200
# Módulo: backend.v0_3.server.app

set -e

# Configuración
PORT=8200
MODULE="backend.v0_3.server.app"
SERVICE_NAME="Server v0.3"

# Función de limpieza al salir (Ctrl+C)
cleanup() {
    echo
    echo "🛑 Deteniendo ${SERVICE_NAME}..."
    if [ ! -z "$SERVER_PID" ]; then
        kill -TERM $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🧹 Revisando procesos previos del ${SERVICE_NAME}..."

# 1) Solo cerrar procesos que ejecuten el módulo Server específico
SERVER_PIDS=$(pgrep -u "$USER" -f "python.* -m.*${MODULE}" 2>/dev/null || true)
if [ ! -z "$SERVER_PIDS" ]; then
    echo "🔎 Encontrado ${SERVICE_NAME} corriendo (PIDs: $SERVER_PIDS)"
    echo "🔪 Cerrando procesos Server previos..."
    echo $SERVER_PIDS | xargs kill -TERM 2>/dev/null || true
    sleep 2
    
    # Verificar que se cerraron
    SERVER_PIDS=$(pgrep -u "$USER" -f "python.* -m.*${MODULE}" 2>/dev/null || true)
    if [ ! -z "$SERVER_PIDS" ]; then
        echo "🔪 Terminando procesos Server persistentes..."
        echo $SERVER_PIDS | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
else
    echo "✅ No hay procesos Server previos corriendo"
fi

# 2) Verificar que el puerto esté libre
if lsof -i :$PORT >/dev/null 2>&1; then
    echo "⚠️  Puerto $PORT ocupado, intentando liberar..."
    PORT_PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ ! -z "$PORT_PIDS" ]; then
        echo "🔪 Cerrando procesos en puerto $PORT..."
        echo $PORT_PIDS | xargs kill -TERM 2>/dev/null || true
        sleep 2
        PORT_PIDS=$(lsof -ti :$PORT 2>/dev/null || true)
        if [ ! -z "$PORT_PIDS" ]; then
            echo "⚠️  Puerto $PORT aún ocupado por procesos: $PORT_PIDS"
            echo "❌ No se puede iniciar ${SERVICE_NAME}"
            exit 1
        fi
    fi
fi

echo "✅ Puerto $PORT liberado"

# 3) Configurar entorno  
export PYTHONPATH="/Users/daniel/Desktop/projects/trading_bot/backend:${PYTHONPATH}"

echo "🚀 Iniciando ${SERVICE_NAME} en puerto $PORT..."
echo "📝 Para detener: Ctrl+C"
echo "─────────────────────────────────────"

# 4) Ejecutar en foreground (no background)
python -m $MODULE &
SERVER_PID=$!

# 5) Esperar y mostrar logs
echo "👁️  PID ${SERVICE_NAME}: $SERVER_PID"
echo "─────────────────────────────────────"

# Mantener el script vivo y mostrar logs
wait $SERVER_PID
