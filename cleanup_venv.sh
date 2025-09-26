#!/bin/bash
# Script para limpiar el entorno virtual

set -euo pipefail

cd "$(dirname "$0")"

VENV_DIR="trading_bot_env"

echo "🧹 Limpiando entorno virtual..."

if [ -d "${VENV_DIR}" ]; then
  echo "🗑️  Eliminando directorio ${VENV_DIR}..."
  rm -rf "${VENV_DIR}"
  echo "✅ Entorno virtual eliminado"
else
  echo "ℹ️  No existe el entorno virtual ${VENV_DIR}"
fi

echo "✅ Limpieza completada"
