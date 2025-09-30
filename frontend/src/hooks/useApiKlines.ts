import API_CONFIG from '@config/api'
import apiClient from '@services/apiClient'
import { useEffect, useState } from 'react'

interface UseApiKlinesReturn {
  candlesData: any[]
  isLoading: boolean
  error: string | null
  refetch: () => void
}

export const useApiKlines = (
  symbol: string = 'DOGEUSDT',
  interval: string = '1m',
  limit: number = 1000
): UseApiKlinesReturn => {
  const [candlesData, setCandlesData] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchKlines = async () => {
    setIsLoading(true)
    setError(null)

    try {
      console.log(`🌱 Cargando datos históricos para ${symbol} con timeframe ${interval}`)

      const response = await apiClient.get<any>(API_CONFIG.ENDPOINTS.KLINES, {
        params: { symbol, interval, limit }
      })

      // El backend devuelve: { status: "success", data: [...], symbol: "...", interval: "...", count: 123 }
      if (
        response.data &&
        response.data.status === 'success' &&
        Array.isArray(response.data.data)
      ) {
        console.log(
          `📊 Klines recibidos: ${response.data.count} velas para ${response.data.symbol} ${response.data.interval}`
        )

        // Transformar datos del backend al formato esperado por CandlestickChart
        const transformedData = response.data.data.map((candle: any) => ({
          time: candle.timestamp, // El backend devuelve 'timestamp', el frontend espera 'time'
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: candle.quote_volume || candle.volume // Usar quote_volume como prioridad, igual que en WebSocket
        }))

        console.log(`🔄 Datos transformados: ${transformedData.length} velas`)
        setCandlesData(transformedData)
      } else if (response.data && response.data.status === 'error') {
        setError(response.data.message || 'Error del servidor')
        setCandlesData([])
      } else {
        setError('Formato de respuesta inválido')
        setCandlesData([])
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch klines'
      setError(errorMessage)
      setCandlesData([])
      console.error('❌ Error al cargar datos históricos:', err)
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
