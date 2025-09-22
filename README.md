# 🤖 TRADING BOT - SISTEMA PLUG-AND-PLAY

## 📋 RESUMEN

Sistema de trading automatizado con bots plug-and-play, frontend React, y backend FastAPI. **90% completado y funcional.**

### 🎯 Características Principales

- **Trading Real** con Binance API
- **Sistema Plug-and-Play** para bots dinámicos
- **Frontend React** con gráficos en tiempo real
- **4 Bots Disponibles** (2 legacy + 2 plug-and-play)
- **Risk Management** completo
- **WebSocket** en tiempo real

---

## 🚀 INICIO RÁPIDO

### 1. Backend

```bash
cd backend
python3 server_simple.py
```

### 2. Frontend

```bash
cd frontend
npm run dev
```

### 3. Acceder

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000

---

## 🤖 BOTS DISPONIBLES

### ✅ Legacy (Funcionando)

- **conservative**: SMA Cross 8/21 + RSI + Volume
- **aggressive**: SMA Cross 5/13 + RSI + Volume

### ⚠️ Plug-and-Play (Con errores)

- **rsibot**: Bot basado en RSI
- **macdbot**: Bot basado en MACD

---

## 📁 ESTRUCTURA

```
trading_bot/
├── backend/
│   ├── server_simple.py          # Servidor principal
│   ├── real_trading_manager.py   # Trading real
│   ├── bot_registry.py           # Sistema plug-and-play
│   ├── bots/                     # Bots dinámicos
│   └── logs/trading_history.json # Historial
├── frontend/
│   └── src/components/           # Componentes React
├── PROJECT_STATUS.md             # Estado detallado
└── QUICK_START.md               # Inicio rápido
```

---

## 🔧 API ENDPOINTS

### Bots

- `GET /api/bots` - Lista todos los bots
- `POST /api/bots/{name}/start` - Iniciar bot
- `GET /api/bots/{name}/signals` - Señales del bot

### Trading

- `GET /bot/status` - Estado completo
- `GET /trading/history` - Historial
- `GET /trading/active-positions` - Posiciones activas

---

## ⚠️ ISSUES CONOCIDOS

1. **Bots RSI/MACD**: Error con numpy arrays
2. **Frontend**: No muestra bots dinámicos

---

## 🎯 PRÓXIMOS PASOS

1. Corregir errores en bots RSI/MACD
2. Actualizar frontend para bots dinámicos
3. Crear más bots (Bollinger, Stochastic, etc.)

---

## 📊 ESTADO ACTUAL

- **Total Bots**: 4
- **Bots Activos**: 0
- **Posiciones**: 0
- **Balance**: ~10.89 USDT
- **PnL**: +0.033 USDT

**Sistema listo para producción con pequeñas correcciones.**
