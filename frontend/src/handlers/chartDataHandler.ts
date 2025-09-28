import { eventBus, EventType } from '../eventBus'
import type { PriceUpdateData } from '../eventBus/types'

/**
 * Handler específico de la aplicación para datos del chart
 * Conecta el chartDataHandler agnóstico con el event bus de la app
 */
export const appChartDataHandler = (rawMessage: any) => {
  // console.log('📊 App chart data handler received raw message:', rawMessage)

  // Procesar mensaje raw del socket y emitir evento tipado
  if (rawMessage.type === 'binance.kline') {
    const kline = rawMessage.data?.k || rawMessage.data
    if (kline?.c) {
      const priceUpdateData: PriceUpdateData = {
        price: Number(kline.c),
        symbol: kline.s || 'DOGEUSDT',
        timestamp: new Date().toISOString(),
        rawData: rawMessage
      }
      eventBus.emit(EventType.PRICE_UPDATE, priceUpdateData)
    }
  } else if (rawMessage.type === 'binance.bookTicker') {
    // Para book ticker, por ahora no hacemos nada
    console.log('📊 Book ticker data received:', rawMessage)
  } else {
    // Para otros tipos de mensajes
    console.log('📊 Unknown message type:', rawMessage.type, rawMessage)
  }
}
