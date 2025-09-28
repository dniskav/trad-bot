// Constantes para tipos de eventos
export const EventType = {
  // Eventos de WebSocket
  WS_BINANCE_KLINE: 'ws:binance:kline',
  WS_BINANCE_BOOK_TICKER: 'ws:binance:book_ticker',
  WS_SERVER_ACCOUNT_BALANCE: 'ws:server:account_balance',
  WS_SERVER_POSITIONS: 'ws:server:positions',
  WS_SERVER_BOT_STATUS: 'ws:server:bot_status',

  // Eventos de API
  API_GET_ACCOUNT_SYNTH: 'api:get:account_synth',
  API_POST_BOT_START: 'api:post:bot_start',
  API_POST_BOT_STOP: 'api:post:bot_stop',
  API_GET_BOT_STATUS: 'api:get:bot_status',
  API_GET_TRADING_HISTORY: 'api:get:trading_history',

  // Eventos de Bots
  BOT_RSI_SIGNAL: 'bot:rsi:signal',
  BOT_RSI_POSITION_OPEN: 'bot:rsi:position_open',
  BOT_RSI_POSITION_CLOSE: 'bot:rsi:position_close',
  BOT_MACD_SIGNAL: 'bot:macd:signal',
  BOT_MACD_POSITION_OPEN: 'bot:macd:position_open',
  BOT_MACD_POSITION_CLOSE: 'bot:macd:position_close',
  BOT_CONSERVATIVE_SIGNAL: 'bot:conservative:signal',
  BOT_AGGRESSIVE_SIGNAL: 'bot:aggressive:signal',

  // Eventos procesados (internos)
  PRICE_UPDATE: 'price_update',
  CONNECTION_UPDATE: 'connection_update',
  BOOK_TICKER_UPDATE: 'book_ticker_update'
} as const

// Type para los valores de EventType
export type EventTypeValue = (typeof EventType)[keyof typeof EventType]

// Interface para eventos del event bus
export interface EventPayload {
  type: EventTypeValue
  data: any
  timestamp?: string
  source?: string
}

// Interface para eventos de WebSocket
export interface WebSocketEvent extends EventPayload {
  type:
    | typeof EventType.WS_BINANCE_KLINE
    | typeof EventType.WS_BINANCE_BOOK_TICKER
    | typeof EventType.WS_SERVER_ACCOUNT_BALANCE
    | typeof EventType.WS_SERVER_POSITIONS
    | typeof EventType.WS_SERVER_BOT_STATUS
  source: 'binance' | 'server'
}

// Interface para eventos de API
export interface ApiEvent extends EventPayload {
  type:
    | typeof EventType.API_GET_ACCOUNT_SYNTH
    | typeof EventType.API_POST_BOT_START
    | typeof EventType.API_POST_BOT_STOP
    | typeof EventType.API_GET_BOT_STATUS
    | typeof EventType.API_GET_TRADING_HISTORY
  source: 'api'
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
}

// Interface para eventos de Bots
export interface BotEvent extends EventPayload {
  type:
    | typeof EventType.BOT_RSI_SIGNAL
    | typeof EventType.BOT_RSI_POSITION_OPEN
    | typeof EventType.BOT_RSI_POSITION_CLOSE
    | typeof EventType.BOT_MACD_SIGNAL
    | typeof EventType.BOT_MACD_POSITION_OPEN
    | typeof EventType.BOT_MACD_POSITION_CLOSE
    | typeof EventType.BOT_CONSERVATIVE_SIGNAL
    | typeof EventType.BOT_AGGRESSIVE_SIGNAL
  source: 'bot'
  botName: string
}

// Union type para todos los eventos
export type AppEvent = WebSocketEvent | ApiEvent | BotEvent | EventPayload

export interface PriceUpdateData {
  price: number
  symbol: string
  timestamp: string
  rawData?: any
}

export interface ConnectionStateData {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
}

export interface BinanceKlineData {
  type: 'binance.kline'
  data: {
    k?: {
      s: string // symbol
      c: string // close price
      t: number // start time
      [key: string]: any
    }
    [key: string]: any
  }
}

export interface BinanceBookTickerData {
  type: 'binance.bookTicker'
  data: {
    s: string // symbol
    a: string // ask price
    b: string // bid price
    [key: string]: any
  }
}

export type BinanceData = BinanceKlineData | BinanceBookTickerData

export interface EventBusHandler {
  (payload: EventPayload): void
}

export interface EventBus {
  on(event: EventTypeValue | string, callback: (data: any) => void): void
  off(event: EventTypeValue | string, callback: (data: any) => void): void
  emit(event: EventTypeValue | string, data: any): void
  addKnownEvent(event: string): void
  getKnownEvents(): string[]
}
