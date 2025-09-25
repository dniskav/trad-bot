#!/bin/bash
# Script para iniciar Server con imports robustos

# Cambiar al directorio del proyecto trading_bot
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

echo "🚀 Iniciando Server v0.2..."
echo "PYTHONPATH: $PYTHONPATH"
python -m backend.v0_2.server.app
