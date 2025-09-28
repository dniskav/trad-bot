import type { BinanceKlineData, EventPayload, PriceUpdateData } from '../eventBus/types'
import { EventType } from '../eventBus/types'

/**
 * Handler para procesar datos del chart
 * Extrae información específica de los datos raw de Binance
 * Es agnóstico a la implementación del event bus
 */
export const handleChartData = (
  payload: EventPayload,
  onPriceUpdate?: (data: PriceUpdateData) => void,
  onConnectionUpdate?: (data: any) => void,
  onRawData?: (message: string, data: any) => void
): void => {
  console.log('📊 Chart data received:', payload.type, payload.data)

  switch (payload.type) {
    case EventType.WS_BINANCE_KLINE:
      processBinanceData(payload.data, onPriceUpdate)
      break

    case EventType.CONNECTION_UPDATE:
      // Emitir estado de conexión
      if (onConnectionUpdate) {
        onConnectionUpdate(payload.data)
      }
      break

    default:
      // Emitir datos raw para otros casos
      if (onRawData) {
        onRawData(payload.type, payload.data)
      }
      break
  }
}

/**
 * Procesa datos específicos de Binance
 */
const processBinanceData = (data: any, onPriceUpdate?: (data: PriceUpdateData) => void): void => {
  if (data.type === 'binance.kline') {
    processKlineData(data, onPriceUpdate)
  } else if (data.type === 'binance.bookTicker') {
    processBookTickerData(data)
  }
}

/**
 * Procesa datos de klines (velas) de Binance
 */
const processKlineData = (
  data: BinanceKlineData,
  onPriceUpdate?: (data: PriceUpdateData) => void
): void => {
  const kline = data.data?.k || data.data
  if (kline?.c && onPriceUpdate) {
    const price = Number(kline.c)
    const symbol = kline.s || 'DOGEUSDT'

    const priceUpdateData: PriceUpdateData = {
      price,
      symbol,
      timestamp: new Date().toISOString(),
      rawData: data
    }

    // Emitir precio procesado
    onPriceUpdate(priceUpdateData)
  }
}

/**
 * Procesa datos de book ticker de Binance
 */
const processBookTickerData = (_data: any): void => {
  // Por ahora no procesamos book ticker
  // Se puede extender en el futuro si es necesario
}
