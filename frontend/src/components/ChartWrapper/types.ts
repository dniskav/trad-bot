export interface ChartWrapperProps {
  symbol?: string
  live?: boolean
  binanceSymbol?: string
  binanceInterval?: string
  enableWebSocket?: boolean
  // Callback genérico que recibe { type, data }
  onData?: (payload: { type: string; data: any }) => void
}

export interface CandlestickData {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

export interface ChartState {
  timeframe: string
  chartRemountKey: number
  isLoading: boolean
  error: string | null
  candlesData: CandlestickData[]
}
