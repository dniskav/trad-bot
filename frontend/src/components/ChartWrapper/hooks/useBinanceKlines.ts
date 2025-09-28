import { useEffect, useState } from 'react'

interface UseBinanceKlinesReturn {
  candlesData: any[]
  isLoading: boolean
  error: string | null
  refetch: () => void
}

export const useBinanceKlines = (
  symbol: string = 'DOGEUSDT',
  interval: string = '1m',
  limit: number = 1000
): UseBinanceKlinesReturn => {
  const [candlesData, setCandlesData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchKlines = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Llamar directamente a la API pública de Binance
      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=${limit}`
      )

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      if (Array.isArray(data)) {
        // Transformar datos de Binance al formato esperado por CandlestickChart
        const transformedData = data.map((candle: any[]) => ({
          time: candle[0], // timestamp de apertura
          open: parseFloat(candle[1]),
          high: parseFloat(candle[2]),
          low: parseFloat(candle[3]),
          close: parseFloat(candle[4]),
          volume: parseFloat(candle[5]) // base volume
        }))

        setCandlesData(transformedData)
      } else {
        setError('Formato de respuesta inválido de Binance')
        setCandlesData([])
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch klines from Binance'
      setError(errorMessage)
      setCandlesData([])
      console.error('❌ Error al cargar datos históricos de Binance:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Cargar datos automáticamente cuando cambian los parámetros
  useEffect(() => {
    fetchKlines()
  }, [symbol, interval, limit])

  return {
    candlesData,
    isLoading,
    error,
    refetch: fetchKlines
  }
}
