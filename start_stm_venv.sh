#!/bin/bash
# Script para iniciar STM con venv y control de procesos

set -euo pipefail

# Cambiar al directorio del proyecto trading_bot
cd "$(dirname "$0")"

# Configuración
PORT=8100
MODULE="backend.v0_2.stm.app"
VENV_DIR="trading_bot_env"

# Función para matar procesos
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

# Función para verificar compatibilidad de Python
check_python_compatibility() {
  echo "🔍 Verificando compatibilidad de Python..."
  python3 -c "
import sys
version = sys.version_info
print(f'Python version: {version.major}.{version.minor}.{version.micro}')
if version < (3, 8):
    print('❌ ERROR: Se requiere Python 3.8 o superior')
    sys.exit(1)
elif version < (3, 8, 10):
    print('⚠️  ADVERTENCIA: Python 3.8.10+ recomendado para mejor compatibilidad')
else:
    print('✅ Python version compatible')
"
}

# Función para crear venv si no existe
create_venv() {
  if [ ! -d "${VENV_DIR}" ]; then
    echo "📦 Creando entorno virtual en ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
    echo "✅ Entorno virtual creado"
  else
    echo "✅ Entorno virtual ya existe en ${VENV_DIR}"
  fi
}

# Función para instalar dependencias
install_deps() {
  echo "📥 Instalando dependencias en el venv..."
  source "${VENV_DIR}/bin/activate"
  
  # Actualizar pip
  pip install --upgrade pip
  
  # Instalar dependencias si existe requirements.txt
  if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
  else
    # Instalar dependencias básicas
    pip install fastapi uvicorn websockets aiohttp python-dotenv
    echo "⚠️  No se encontró requirements.txt, instalando dependencias básicas"
  fi
  
  deactivate
  echo "✅ Dependencias instaladas"
}

# Función para activar venv y ejecutar
run_with_venv() {
  echo "🚀 Iniciando STM en puerto ${PORT} con venv..."
  
  # Activar venv
  source "${VENV_DIR}/bin/activate"
  
  # Configurar PYTHONPATH
  export PYTHONPATH="$(pwd)"
  echo "PYTHONPATH: $PYTHONPATH"
  echo "Python: $(which python)"
  echo "Pip: $(which pip)"
  
  # Ejecutar el STM
  python -m ${MODULE}
}

echo "🧹 Revisando procesos previos del STM..."

# 1) Cerrar procesos que ejecuten el módulo del STM
if pgrep -u "$USER" -fl "python.*${MODULE}" >/dev/null 2>&1; then
  echo "🔎 Encontrado ${MODULE} corriendo"
  PIDS=$(pgrep -u "$USER" -f "python.*${MODULE}")
  kill_pids "$PIDS"
fi

# 2) Liberar el puerto si está ocupado
if lsof -i :${PORT} -sTCP:LISTEN -u "$USER" >/dev/null 2>&1; then
  echo "🔧 Liberando puerto ${PORT} ocupado"
  PIDS=$(lsof -t -i :${PORT} -sTCP:LISTEN -u "$USER")
  kill_pids "$PIDS"
fi

# 3) Verificar compatibilidad y crear venv
check_python_compatibility
create_venv
install_deps

# 4) Ejecutar con venv
run_with_venv
