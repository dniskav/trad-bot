#!/bin/bash
# Script para iniciar STM con imports robustos

# Cambiar al directorio del proyecto trading_bot
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

echo "🚀 Iniciando STM..."
echo "PYTHONPATH: $PYTHONPATH"
python -m backend.v0_2.stm.app
