// API Configuration
export const API_CONFIG = {
  BASE_URL:
    typeof window !== 'undefined' && window.location.hostname
      ? `${window.location.protocol}//${window.location.hostname}:3000`
      : 'http://localhost:3000',

  ENDPOINTS: {
    BOTS: '/api/bots',
    BOT_PROCESS_INFO: '/api/bots/process-info',
    BOT_START: (botName: string) => `/api/${botName}/start`,
    BOT_STOP: (botName: string) => `/api/${botName}/stop`,
    BOT_CONFIG: (botName: string) => `/api/${botName}/config`,
    // v0.2 Strategy Engine (server)
    STRATEGIES_LOADED: '/strategies/',
    STRATEGIES_CONFIGS: '/strategies/configs',
    STRATEGY_LOAD: (name: string) => `/strategies/load/${name}`,
    STRATEGY_UNLOAD: (name: string) => `/strategies/unload/${name}`,
    STRATEGY_START: (name: string) => `/strategies/${name}/start`,
    STRATEGY_STOP: (name: string) => `/strategies/${name}/stop`,
    POSITION_INFO: '/api/position-info',
    TRADING_HISTORY: '/api/trading/history',
    MARGIN_INFO: '/api/margin-info',
    KLINES: '/api/klines',
    POSITIONS: '/api/positions',
    POSITIONS_OPEN: '/api/positions/open',
    POSITIONS_CLOSE: '/api/positions/close',
    ACCOUNT_SYNTH: '/account/synth'
  },

  TIMEOUT: 30000, // 30 seconds (Binance can be slow)
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000 // 1 second
}

export default API_CONFIG
