#!/bin/bash

# Script para arreglar el error "Address already in use" en puertos del proyecto
# Autor: Trading Bot Assistant
# Fecha: $(date)

# Uso: ./fix_port.sh [--stm | --server | --api | --ports "p1 p2 ..."] [--force]
# Sin parámetros repara todos (8000, 8100, 8200)
# --force: omite confirmaciones (usar con precaución)

PORTS_DEFAULT=(8000 8100 8200)
PORTS=()
FORCE_MODE=false
DRY_RUN=false

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
    --force)
      FORCE_MODE=true
      shift ;;
    --dry-run)
      DRY_RUN=true
      shift ;;
    *)
      echo "⚠️  Opción desconocida: $1 (se ignorará)"; shift ;;
  esac
done

if [[ ${#PORTS[@]} -eq 0 ]]; then
  PORTS=(${PORTS_DEFAULT[@]})
fi

echo "🔧 Arreglando puertos: ${PORTS[*]}"
if [ "$FORCE_MODE" = true ]; then
    echo "⚠️  MODO FORCE ACTIVADO - Se omitirán confirmaciones"
fi
if [ "$DRY_RUN" = true ]; then
    echo "👟 DRY RUN - No se terminará ningún proceso"
fi

# Ruta absoluta del proyecto (raíz del repo)
PROJECT_PATH=$(pwd)

# Helper: verificar si un PID es un proceso Python del proyecto
is_project_python_pid() {
    local pid="$1"
    local cmd
    cmd=$(ps -p "$pid" -o command= 2>/dev/null || true)
    if [[ -z "$cmd" ]]; then
        return 1
    fi
    if [[ "$cmd" == *python* ]] && [[ "$cmd" == *"$PROJECT_PATH"* ]]; then
        return 0
    fi
    return 1
}

# Función para mostrar procesos en el puerto 8000
show_port_processes() {
    for p in "${PORTS[@]}"; do
      echo "📋 Procesos (Python del proyecto) usando el puerto $p:"
      lsof -ti:$p | while read pid; do
        if [ -n "$pid" ] && is_project_python_pid "$pid"; then
          proc_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "Proceso no encontrado")
          echo "  PID: $pid"
          echo "    CMD: $proc_cmd"
        fi
      done || true
    done
}

# Función para matar procesos en el puerto específico
kill_port_processes() {
    for p in "${PORTS[@]}"; do
      echo "🛑 Matando procesos en el puerto $p..."
      any_killed=false
      lsof -ti:$p | while read pid; do
        if [ -n "$pid" ] && is_project_python_pid "$pid"; then
          proc_cmd=$(ps -p "$pid" -o command= 2>/dev/null || echo "Proceso no encontrado")
          if [ "$DRY_RUN" = true ]; then
            echo "📝 DRY-RUN: Se terminaría PID $pid"
          elif [ "$FORCE_MODE" = true ]; then
            echo "🔪 Terminando PID $pid (force)"
            kill -9 "$pid" 2>/dev/null || true
            any_killed=true
          else
            echo "⚠️  Terminar PID $pid?"
            echo "    $proc_cmd"
            printf "    Confirmar (y/N): "
            read -r response
            if [[ "$response" =~ ^[Yy]$ ]]; then
              kill -9 "$pid" 2>/dev/null || true
              any_killed=true
              echo "   ✅ Terminado $pid"
            else
              echo "   ⏭️  Omitido $pid"
            fi
          fi
        fi
      done
      if [ "$DRY_RUN" = true ]; then
        echo "ℹ️  DRY-RUN: listado completado en $p"
      elif [ "$any_killed" = true ]; then
        sleep 1
        echo "✅ Procesos Python del proyecto terminados en $p"
      else
        echo "ℹ️  No se encontraron procesos Python del proyecto en $p"
      fi
    done
}

# Función para matar procesos específicos del servidor
kill_server_processes() {
    echo "🛑 Matando procesos específicos del servidor..."
    echo "📁 Proyecto: $PROJECT_PATH"

    # Enumerar procesos Python del proyecto y filtrar por patrones del server/STM
    mapfile -t lines < <(pgrep -fl python 2>/dev/null | grep -F "$PROJECT_PATH" || true)
    if [ ${#lines[@]} -eq 0 ]; then
      echo "ℹ️  No se encontraron procesos Python del proyecto activos"
      return 0
    fi

    for line in "${lines[@]}"; do
      pid=$(echo "$line" | awk '{print $1}')
      cmd=${line#* } || true
      if [[ -z "$pid" ]]; then continue; fi
      # Patrones del proyecto a considerar seguros
      if [[ "$cmd" == *"backend.v0_2.server.app"* ]] || \
         [[ "$cmd" == *"backend.v0_2.stm.app"* ]] || \
         [[ "$cmd" == *"server.py"* ]] || \
         [[ "$cmd" == *"app.py"* ]] || \
         [[ "$cmd" == *"real_trading_manager"* ]] || \
         [[ "$cmd" == *"trading_tracker"* ]]; then
        if [ "$DRY_RUN" = true ]; then
          echo "📝 DRY-RUN: Se terminaría PID $pid"
        elif [ "$FORCE_MODE" = true ]; then
          echo "🔪 Terminando PID $pid (force)"
          kill -9 "$pid" 2>/dev/null || true
        else
          echo "⚠️  Terminar proceso $pid?"
          echo "    $cmd"
          printf "    Confirmar (y/N): "
          read -r response
          if [[ "$response" =~ ^[Yy]$ ]]; then
            kill -9 "$pid" 2>/dev/null || true
            echo "   ✅ Terminado $pid"
          else
            echo "   ⏭️  Omitido $pid"
          fi
        fi
      fi
    done

    sleep 1
    echo "✅ Revisión de procesos del servidor completada"
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
    # Buscar procesos Python del proyecto que parezcan auxiliares/huérfanos
    mapfile -t lines < <(pgrep -fl python 2>/dev/null | grep -F "$PROJECT_PATH" || true)
    for line in "${lines[@]}"; do
      pid=$(echo "$line" | awk '{print $1}')
      cmd=${line#* } || true
      if [[ -z "$pid" ]]; then continue; fi
      # Patrones seguros (multiprocessing y utilidades del proyecto)
      if [[ "$cmd" == *"multiprocessing.spawn_main"* ]] || \
         [[ "$cmd" == *"multiprocessing.resource_tracker"* ]] || \
         [[ "$cmd" == *"trading"* && "$cmd" == *"tracker"* ]] || \
         [[ "$cmd" == *"backend.v0_2"* ]]; then
        if [ "$DRY_RUN" = true ]; then
          echo "📝 DRY-RUN: Se terminaría auxiliar PID $pid"
        elif [ "$FORCE_MODE" = true ]; then
          echo "🔪 Terminando auxiliar PID $pid (force)"
          kill -9 "$pid" 2>/dev/null || true
        else
          echo "⚠️  Terminar auxiliar $pid?"
          echo "    $cmd"
          printf "    Confirmar (y/N): "
          read -r response
          if [[ "$response" =~ ^[Yy]$ ]]; then
            kill -9 "$pid" 2>/dev/null || true
            echo "   ✅ Terminado $pid"
          else
            echo "   ⏭️  Omitido $pid"
          fi
        fi
      fi
    done
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
        echo "   ./start_stm_v2.sh"
        echo "   ./start_server_v2.sh"
        echo "   o"
        echo "   ./start_server.sh --start"
        echo "   ./start_server.sh --foreground"
        echo ""
        echo "🔧 Para usar el script en modo automático:"
        echo "   ./fix_port.sh --force"
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
