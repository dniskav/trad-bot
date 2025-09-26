#!/bin/bash
# Script para iniciar Server con imports robustos y control de procesos

set -euo pipefail

# Cambiar al directorio del proyecto trading_bot
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

PORT=8200
MODULE="backend.v0_2.server.app"

kill_pids() {
  local pids="$1"
  if [ -z "${pids}" ]; then return 0; fi
  echo "🔪 Enviando SIGTERM a: ${pids}"
  kill ${pids} >/dev/null 2>&1 || true
  sleep 0.3
  # Forzar si siguen vivos
  for pid in ${pids}; do
    if kill -0 ${pid} >/dev/null 2>&1; then
      echo "⚠️  Forzando SIGKILL a ${pid}"
      kill -9 ${pid} >/dev/null 2>&1 || true
    fi
  done
}

echo "🧹 Revisando procesos previos del Server..."

# 1) Cerrar procesos que ejecuten el módulo del server
if pgrep -u "$USER" -fl "python3 -m ${MODULE}" >/dev/null 2>&1; then
  echo "🔎 Encontrado ${MODULE} corriendo"
  PIDS=$(pgrep -u "$USER" -f "python3 -m ${MODULE}")
  kill_pids "$PIDS"
fi

# 2) Liberar el puerto si está ocupado
if lsof -i :${PORT} -sTCP:LISTEN -u "$USER" >/dev/null 2>&1; then
  echo "🔧 Liberando puerto ${PORT} ocupado"
  PIDS=$(lsof -t -i :${PORT} -sTCP:LISTEN -u "$USER")
  kill_pids "$PIDS"
fi

echo "🚀 Iniciando Server v0.2 en puerto ${PORT}..."
echo "PYTHONPATH: $PYTHONPATH"
python3 -m ${MODULE}
