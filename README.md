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
python3 server.py
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
│   ├── server.py                 # Servidor principal
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
=======
# SMA Cross Trading Bot

A cryptocurrency trading bot that implements a Simple Moving Average (SMA) crossover strategy for Binance Futures.

## Features

- **SMA Crossover Strategy**: Uses fast (5-period) and slow (20-period) moving averages
- **Binance Futures Integration**: Connects to Binance USDT-M Futures testnet
- **Risk Management**: Configurable position sizing and risk per trade
- **Real-time Monitoring**: Live price tracking and signal generation
- **Trade Logging**: Comprehensive trade history and performance metrics
- **GitFlow Workflow**: Proper branching strategy for development

## Prerequisites

- Python 3.8+
- Binance Futures testnet account
- API keys for Binance testnet

## Installation

1. Clone the repository:

```bash
git clone https://github.com/dniskav/trad-bot.git
cd trad-bot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Binance API credentials:

```bash
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

## Usage

### Basic Usage

```bash
python sma_cross_bot.py
```

### Synthetic Test

```bash
python sma_cross_bot.py --synthetic
```

### Configuration

Key parameters in `sma_cross_bot.py`:

- `SYMBOL`: Trading pair (default: "BTCUSDT")
- `INTERVAL`: Timeframe (default: "1m")
- `FAST_WINDOW`: Fast SMA period (default: 5)
- `SLOW_WINDOW`: Slow SMA period (default: 20)
- `CAPITAL`: Virtual capital (default: 1000)
- `RISK_PER_TRADE`: Risk percentage per trade (default: 0.01)

## Project Structure

```
trad-bot/
├── sma_cross_bot.py      # Main trading bot
├── metrics_logger.py     # Trade logging and metrics
├── config.py            # Configuration management
├── utils.py             # Utility functions
├── compare_metrics.py   # Performance comparison tools
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## GitFlow Workflow

This project uses GitFlow for development:

- `master`: Production-ready code
- `develop`: Development branch
- `feature/*`: New features
- `release/*`: Release preparation
- `hotfix/*`: Critical bug fixes

### Common GitFlow Commands

```bash
# Start a new feature
git flow feature start feature-name

# Finish a feature
git flow feature finish feature-name

# Start a release
git flow release start 1.0.0

# Finish a release
git flow release finish 1.0.0

# Start a hotfix
git flow hotfix start hotfix-name

# Finish a hotfix
git flow hotfix finish hotfix-name
```

## Risk Warning

⚠️ **This is experimental software for educational purposes only.**

- Only use with testnet accounts
- Never use real money without thorough testing
- Cryptocurrency trading involves significant risk
- Past performance does not guarantee future results

## Contributing

1. Fork the repository
2. Create a feature branch: `git flow feature start feature-name`
3. Make your changes
4. Commit your changes: `git commit -am 'Add feature'`
5. Push to the branch: `git push origin feature/feature-name`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions, please open an issue on GitHub.
