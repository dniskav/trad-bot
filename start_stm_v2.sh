#!/bin/bash

# Script para iniciar STM (Simulated Trading Manager)
# Puerto: 8100
# Módulo: backend.v0_2.stm.app

set -e

# Configuración
PORT=8100
MODULE="backend.v0_2.stm.app"
SERVICE_NAME="STM"

# Función de limpieza al salir (Ctrl+C)
cleanup() {
    echo
    echo "🛑 Deteniendo ${SERVICE_NAME}..."
    if [ ! -z "$STM_PID" ]; then
        kill -TERM $STM_PID 2>/dev/null || true
        wait $STM_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🧹 Revisando procesos previos del ${SERVICE_NAME}..."

# 1) Solo cerrar procesos que ejecuten el módulo STM específico
STM_PIDS=$(pgrep -u "$USER" -f "python.* -m.*${MODULE}" 2>/dev/null || true)
if [ ! -z "$STM_PIDS" ]; then
    echo "🔎 Encontrado ${SERVICE_NAME} corriendo (PIDs: $STM_PIDS)"
    echo "🔪 Cerrando procesos STM previos..."
    echo $STM_PIDS | xargs kill -TERM 2>/dev/null || true
    sleep 2
    
    # Verificar que se cerraron
    STM_PIDS=$(pgrep -u "$USER" -f "python.* -m.*${MODULE}" 2>/dev/null || true)
    if [ ! -z "$STM_PIDS" ]; then
        echo "🔪 Terminando procesos STM persistentes..."
        echo $STM_PIDS | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
else
    echo "✅ No hay procesos STM previos corriendo"
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
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

echo "🚀 Iniciando ${SERVICE_NAME} en puerto $PORT..."
echo "📝 Para detener: Ctrl+C"
echo "─────────────────────────────────────"

# 4) Ejecutar en foreground (no background)
python -m $MODULE &
STM_PID=$!

# 5) Esperar y mostrar logs
echo "👁️  PID ${SERVICE_NAME}: $STM_PID"
echo "─────────────────────────────────────"

# Mantener el script vivo y mostrar logs
wait $STM_PID