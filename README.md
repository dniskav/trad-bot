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
git clone <repository-url>
cd trading_bot
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
trading_bot/
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
