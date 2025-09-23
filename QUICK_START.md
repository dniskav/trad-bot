# 🚀 QUICK START - TRADING BOT

## ⚡ INICIO RÁPIDO

### 1. Iniciar Backend

```bash
cd backend
python3 server.py
```

### 2. Iniciar Frontend (nueva terminal)

```bash
cd frontend
npm run dev
```

### 3. Acceder al Sistema

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000

---

## 🎯 ESTADO ACTUAL

### ✅ FUNCIONANDO

- Sistema de trading real con Binance
- Frontend React con gráficos en tiempo real
- 2 bots legacy (conservative, aggressive)
- Sistema plug-and-play implementado
- API REST completa
- WebSocket en tiempo real

### ⚠️ PENDIENTE

- Corregir errores en bots RSI/MACD
- Frontend para bots dinámicos

---

## 🤖 BOTS DISPONIBLES

### Legacy (Funcionando)

- **conservative**: SMA Cross 8/21 + RSI + Volume
- **aggressive**: SMA Cross 5/13 + RSI + Volume

### Plug-and-Play (Con errores)

- **rsibot**: Bot basado en RSI
- **macdbot**: Bot basado en MACD

---

## 🔧 COMANDOS ÚTILES

```bash
# Ver bots disponibles
curl http://localhost:8000/api/bots

# Estado completo
curl http://localhost:8000/bot/status

# Activar bot legacy
curl -X POST http://localhost:8000/api/bot-control/conservative/start

# Ver historial
curl http://localhost:8000/trading/history
```

---

## 📁 ARCHIVOS CLAVE

- `backend/server.py` - Servidor principal
- `backend/real_trading_manager.py` - Trading real
- `backend/bot_registry.py` - Sistema plug-and-play
- `frontend/src/components/BotSignals.tsx` - Control de bots
- `PROJECT_STATUS.md` - Estado detallado del proyecto

---

## 🎯 PRÓXIMO PASO

**Corregir errores en bots RSI/MACD** para completar el sistema plug-and-play.

**El sistema está 90% completo y funcional.**
