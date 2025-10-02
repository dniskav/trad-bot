# 🤖 Scripts de Utilidades del Trading Bot

Esta colección de scripts facilita la gestión rápida y efectiva del sistema de trading bot.

## 📁 Scripts Disponibles

### 🔪 `kill_processes.sh` - Gestión de Procesos

Termina procesos específicos o todos los procesos del trading bot.

```bash
# Ver procesos corriendo
./kill_processes.sh

# Terminar solo servidor
./kill_processes.sh server

# Terminar solo STM
./kill_processes.sh stm

# Terminar todos los procesos
./kill_processes.sh all
```

**Características:**

- ⚡ Terminación con SIGTERM seguido de SIGKILL si es necesario
- 🔍 Verificación de estado después de cada acción
- 🚦 Verificación automática de puertos liberados
- 📋 Información detallada de procesos y tiempos de ejecución

---

### 🔌 `check_ports.sh` - Gestión de Puertos

Verifica y gestiona puertos utilizados por el sistema.

```bash
# Verificar estado de puertos
./check_ports.sh

# Liberar puertos específicos
./check_ports.sh free

# Forzar liberación de todos los puertos
./check_ports.sh free-all
```

**Características:**

- 🔍 Verificación completa de puertos 8100 (STM) y 8200 (Servidor)
- 🌐 Información de otros puertos comunes (3000, 5173, 8080, etc.)
- ⚡ Liberación inteligente con verificación de persistencia
- 📊 Estado visual claro con colores

---

### 🛠️ `trading_utils.sh` - Utilidades Generales

Panel de control completo para gestión del sistema.

```bash
# Ver estado general
./trading_utils.sh status

# Verificar salud de servicios
./trading_utils.sh health

# Verificar conectividad con Binance
./trading_utils.sh connectivity

# Iniciar todos los servicios
./trading_utils.sh start

# Detener todos los servicios
./trading_utils.sh stop

# Reiniciar sistema completo
./trading_utils.sh restart

# Reset completo (⚠️ CUIDADO)
./trading_utils.sh reset
```

**Características:**

- 📊 Dashboard completo de estado del sistema
- 🏥 Verificación de salud de APIs y servicios
- 🌐 Test de conectividad con Binance
- 🔄 Control completo del ciclo de vida del sistema
- ⚠️ Funciones de mantenimiento avanzadas

---

## 🚀 Uso Rápido

### Situación: Proceso "colgado" que no responde a Ctrl+C

```bash
# Solución rápida
./kill_processes.sh [proceso]    # Termina proceso específico
./check_ports.sh free            # Libera puerto
./trading_utils.sh restart      # Reinicia todo limpio
```

### Situación: Puerto ocupado al iniciar servicios

```bash
# Solución rápida
./check_ports.sh                # Ver qué usa el puerto
./kill_processes.sh all         # Terminar todos los procesos
./check_ports.sh                # Verificar que quedó libre
```

### Situación: Servicios no responden o hay errores de conectividad

```bash
# Diagnóstico completo
./trading_utils.sh status       # Ver estado general
./trading_utils.sh health       # Verificar APIs
./trading_utils.sh connectivity # Testar Binance
```

### Situación: Sistema completamente roto/reset completo

```bash
# Reset total
./trading_utils.sh stop         # Detener todo
./trading_utils.sh reset        # Reset datos + reinicio
```

---

## 📋 Comandos de Emergencia

### 🔥 Cuando todo está roto:

```bash
# Opción nuclear
./trading_utils.sh reset        # ESCRIBE 'RESET' para confirmar

# O manual paso a paso
./kill_processes.sh all         # Terminar procesos
sleep 3
./check_ports.sh free-all       # Liberar puertos
./start_stm_v2.sh &            # Iniciar STM en background
sleep 5
./start_server_v2.sh &         # Iniciar Server en background
```

### 🚨 Cuando un proceso no cierra con Ctrl+C:

```bash
# Identificar proceso
ps aux | grep python | grep backend

# Terminar por PID específico
kill -9 [PID]

# O usar los scripts automáticos
./kill_processes.sh all
```

---

## 🎯 Casos de Uso Comunes

| Problema              | Comando                           | Descripción                |
| --------------------- | --------------------------------- | -------------------------- |
| Puerto ocupado        | `./check_ports.sh free`           | Libera puertos específicos |
| Proceso colgado       | `./kill_processes.sh all`         | Termina todos los procesos |
| Sistema lento         | `./trading_utils.sh restart`      | Reinicio completo          |
| APIs no responden     | `./trading_utils.sh health`       | Diagnóstico de servicios   |
| Problemas con Binance | `./trading_utils.sh connectivity` | Test de conectividad       |
| Reset necesario       | `./trading_utils.sh reset`        | Reset datos + restart      |
| Estado general        | `./trading_utils.sh status`       | Dashboard completo         |

---

## 🔧 Scripts Originales del Sistema

Los siguientes scripts siguen funcionando como siempre:

- `start_stm_v2.sh` - Inicia STM (sin venv)
- `start_server_v2.sh` - Inicia Server (sin venv)
- `start_stm_venv.sh` - Inicia STM (con venv)
- `start_server_venv.sh` - Inicia Server (con venv)

---

## ⚡ Atajos Útiles

```bash
# Crear alias en tu shell profile (.zshrc, .bashrc, etc.)
alias killserver="./kill_processes.sh server"
alias killstm="./kill_processes.sh stm"
alias killall="./kill_processes.sh all"
alias ports="./check_ports.sh"
alias status="./trading_utils.sh status"
alias health="./trading_utils.sh health"
alias restart="./trading_utils.sh restart"

# Ahora puedes usar simplemente:
killall           # En lugar de ./kill_processes.sh all
ports            # En lugar de ./check_ports.sh
status           # En lugar de ./trading_utils.sh status
```

---

## 💡 Tips y Trucos

1. **Siempre verifica después de cambios:**

   ```bash
   ./trading_utils.sh status && ./trading_utils.sh health
   ```

2. **Para debugging en tiempo real:**

   - Mantén `./start_stm_v2.sh` en una terminal
   - Mantén `./start_server_v2.sh` en otra terminal
   - Usa los scripts utils en una tercera terminal

3. **Verificación rápida de puertos ocupados:**

   ```bash
   lsof -i :8200 -i :8100  # Ver ambos puertos
   ```

4. **Procesos zombie o muy persistentes:**
   ```bash
   ps aux | grep python | grep [PID]  # Verificar si sigue
   sudo kill -9 [PID]                 # Force kill si es necesario
   ```

---

## 🆘 Troubleshooting

### Problema: Scripts no ejecutables

```bash
chmod +x *.sh
```

### Problema: Permisos insuficientes

```bash
# Los scripts están diseñados para el usario actual
# Si hay problemas:
sudo chown -R $(whoami):$(whoami) .
```

### Problema: Comandos no encontrados

```bash
# Verificar ubicación
pwd  # Debe estar en /Users/daniel/Desktop/projects/trading_bot
ls -la *.sh  # Deben aparecer todos los scripts
```

---

¿Necesitas ayuda con algún script específico? Usa `./[script].sh help` para ver la ayuda detallada.
