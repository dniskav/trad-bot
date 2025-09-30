#!/bin/bash
# Script para iniciar STM con imports robustos y control de procesos

set -euo pipefail

# Cambiar al directorio del proyecto trading_bot
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"
PROJECT_PATH="$(pwd)"

PORT=8100
MODULE="backend.v0_2.stm.app"

kill_pids() {
  local pids="$1"
  if [ -z "${pids}" ]; then return 0; fi
  echo "🔪 Enviando SIGTERM a: ${pids}"
  kill ${pids} >/dev/null 2>&1 || true
  sleep 0.3
  for pid in ${pids}; do
    if kill -0 ${pid} >/dev/null 2>&1; then
      echo "⚠️  Forzando SIGKILL a ${pid}"
      kill -9 ${pid} >/dev/null 2>&1 || true
    fi
  done
}

echo "🧹 Revisando procesos previos del STM..."

# 1) Cerrar procesos que ejecuten el módulo del STM
if pgrep -u "$USER" -fl "python.* -m ${MODULE}" >/dev/null 2>&1; then
  echo "🔎 Encontrado ${MODULE} corriendo"
  PIDS=$(pgrep -u "$USER" -f "python.* -m ${MODULE}")
  kill_pids "$PIDS"
fi

# 2) Liberar el puerto si está ocupado
if lsof -i :${PORT} -sTCP:LISTEN -u "$USER" >/dev/null 2>&1; then
  echo "🔧 Liberando puerto ${PORT} ocupado"
  FILTERED_PIDS=""
  while read -r pid; do
    if [ -n "$pid" ]; then
      cmd=$(ps -p "$pid" -o command= 2>/dev/null || true)
      if [[ "$cmd" == *python* ]] && [[ "$cmd" == *"$PROJECT_PATH"* ]]; then
        FILTERED_PIDS+="$pid "
      fi
    fi
  done < <(lsof -t -i :${PORT} -sTCP:LISTEN -u "$USER")
  kill_pids "$FILTERED_PIDS"
fi

echo "🚀 Iniciando STM en puerto ${PORT}..."
echo "PYTHONPATH: $PYTHONPATH"
exec python3 -m ${MODULE}
