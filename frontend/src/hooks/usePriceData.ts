import { useEffect, useState } from 'react'
import { eventBus, EventType } from '../eventBus'

interface PriceData {
  price: number | null
  symbol: string | null
  timestamp: string | null
  isConnected: boolean
}

export const usePriceData = (symbol: string = 'DOGEUSDT') => {
  const [priceData, setPriceData] = useState<PriceData>({
    price: null,
    symbol: null,
    timestamp: null,
    isConnected: false
  })

  useEffect(() => {
    const handlePriceUpdate = (data: any) => {
      if (data.symbol === symbol) {
        setPriceData((prev) => ({
          ...prev,
          price: data.price,
          symbol: data.symbol,
          timestamp: data.timestamp
        }))
      }
    }

    const handleConnectionUpdate = (data: any) => {
      setPriceData((prev) => ({
        ...prev,
        isConnected: data.isConnected
      }))
    }

    eventBus.on(EventType.PRICE_UPDATE, handlePriceUpdate)
    eventBus.on(EventType.CONNECTION_UPDATE, handleConnectionUpdate)

    return () => {
      eventBus.off(EventType.PRICE_UPDATE, handlePriceUpdate)
      eventBus.off(EventType.CONNECTION_UPDATE, handleConnectionUpdate)
    }
  }, [symbol])

  return priceData
}
