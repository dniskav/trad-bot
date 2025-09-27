// API Configuration
export const API_CONFIG = {
  BASE_URL:
    typeof window !== 'undefined' && window.location.hostname
      ? `${window.location.protocol}//${window.location.hostname}:8000`
      : 'http://localhost:8000',

  ENDPOINTS: {
    BOTS: '/api/bots',
    BOT_PROCESS_INFO: '/api/bots/process-info',
    BOT_START: (botName: string) => `/api/${botName}/start`,
    BOT_STOP: (botName: string) => `/api/${botName}/stop`,
    BOT_CONFIG: (botName: string) => `/api/${botName}/config`,
    POSITION_INFO: '/api/position-info',
    TRADING_HISTORY: '/api/trading/history',
    MARGIN_INFO: '/api/margin-info',
    KLINES: '/api/klines'
  },

  TIMEOUT: 30000, // 30 seconds (Binance can be slow)
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000 // 1 second
}

export default API_CONFIG
