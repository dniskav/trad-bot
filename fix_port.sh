#!/bin/bash

# Script para arreglar el error "Address already in use" en puertos del proyecto
# Autor: Trading Bot Assistant
# Fecha: $(date)

# Uso: ./fix_port.sh [--stm | --server | --api | --ports "p1 p2 ..."]
# Sin parámetros repara todos (8000, 8100, 8200)

PORTS_DEFAULT=(8000 8100 8200)
PORTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stm)
      PORTS+=(8100)
      shift ;;
    --server)
      PORTS+=(8200)
      shift ;;
    --api)
      PORTS+=(8000)
      shift ;;
    --ports)
      shift
      # siguiente argumento con lista de puertos separados por espacio
      for p in $1; do PORTS+=($p); done
      shift ;;
    *)
      echo "⚠️  Opción desconocida: $1 (se ignorará)"; shift ;;
  esac
done

if [[ ${#PORTS[@]} -eq 0 ]]; then
  PORTS=(${PORTS_DEFAULT[@]})
fi

echo "🔧 Arreglando puertos: ${PORTS[*]}"

# Función para mostrar procesos en el puerto 8000
show_port_processes() {
    for p in "${PORTS[@]}"; do
      echo "📋 Procesos usando el puerto $p:"
      lsof -ti:$p | while read pid; do
        if [ ! -z "$pid" ]; then
            echo "  PID: $pid - $(ps -p $pid -o comm= 2>/dev/null || echo 'Proceso no encontrado')"
        fi
      done
    done
}

# Función para matar procesos en el puerto 8000
kill_port_processes() {
    for p in "${PORTS[@]}"; do
      echo "🛑 Matando procesos en el puerto $p..."
      pids=$(lsof -ti:$p)
      if [ ! -z "$pids" ]; then
          echo "$pids" | xargs kill -9 2>/dev/null
          sleep 1
          echo "✅ Procesos terminados en $p"
      else
          echo "ℹ️  No hay procesos usando el puerto $p"
      fi
    done
}

# Función para matar procesos específicos del servidor
kill_server_processes() {
    echo "🛑 Matando procesos específicos del servidor..."
    
    # Matar procesos de uvicorn
    pkill -f "uvicorn.*backend.v0_2" 2>/dev/null
    pkill -f "uvicorn.*8100" 2>/dev/null
    pkill -f "uvicorn.*8200" 2>/dev/null
    pkill -f "python.*server.py" 2>/dev/null
    
    # Matar procesos de trading bot
    pkill -f "trading.*bot" 2>/dev/null
    pkill -f "real_trading_manager" 2>/dev/null
    pkill -f "trading_tracker" 2>/dev/null
    
    sleep 2
    echo "✅ Procesos del servidor terminados"
}

# Función para verificar si el puerto está libre
check_port_free() {
    ok=1
    for p in "${PORTS[@]}"; do
      if lsof -ti:$p >/dev/null 2>&1; then
        echo "❌ El puerto $p aún está en uso"; ok=0
      else
        echo "✅ El puerto $p está libre"
      fi
    done
    [ $ok -eq 1 ]
}

# Función para limpiar procesos Python huérfanos
cleanup_python_processes() {
    echo "🧹 Limpiando procesos Python huérfanos..."
    
    # Procesos de multiprocessing
    pkill -f "multiprocessing.spawn_main" 2>/dev/null
    pkill -f "multiprocessing.resource_tracker" 2>/dev/null
    
    # Procesos de trading
    pkill -f "trading.*tracker" 2>/dev/null
    pkill -f "bot.*agresivo" 2>/dev/null
    pkill -f "bot.*conservador" 2>/dev/null
    
    sleep 1
    echo "✅ Limpieza completada"
}

# Función principal
main() {
    echo "=========================================="
    echo "🔧 FIX PORTS - Trading Bot"
    echo "=========================================="
    
    # Mostrar procesos actuales
    show_port_processes
    
    # Limpiar procesos Python huérfanos
    cleanup_python_processes
    
    # Matar procesos específicos del servidor
    kill_server_processes
    
    # Matar cualquier proceso en los puertos declarados
    kill_port_processes
    
    # Verificar que el puerto esté libre
    if check_port_free; then
        echo ""
        echo "🎉 ¡Puertos liberados exitosamente!"
        echo ""
        echo "💡 Ahora puedes iniciar el servidor con:"
        echo "   ./start_server.sh --start"
        echo "   o"
        echo "   ./start_server.sh --foreground"
        echo ""
    else
        echo ""
        echo "⚠️  Algún puerto aún está en uso. Intenta:"
        echo "   1. Reiniciar tu terminal"
        echo "   2. Ejecutar: sudo lsof -ti:<PUERTO> | xargs sudo kill -9"
        echo "   3. Reiniciar tu computadora si es necesario"
        echo ""
    fi
}

# Ejecutar función principal
main
