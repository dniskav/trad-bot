export interface TradingSignal {
  time: number
  type: 'BUY' | 'SELL' | 'HOLD'
  bot: 'conservative' | 'aggressive'
  price: number
  reason?: string
  confidence?: number
}

export interface TechnicalIndicators {
  sma_fast: number[]
  sma_slow: number[]
  rsi: number[]
  volume: number[]
  timestamps: number[]
}

export interface CandlestickChartProps {
  symbol?: string
  interval?: string
  timeframe?: string
  signals?: TradingSignal[]
  candlesData?: any[]
  indicatorsData?: any
  onTimeframeChange?: (timeframe: string) => void
  live?: boolean
  binanceSymbol?: string
  binanceInterval?: string
}
