import { useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface KlinesResponse {
  status: string
  data: any[]
}

interface UseApiKlinesReturn {
  fetchKlines: (symbol: string, interval: string, limit?: number) => Promise<any[] | null>
  isLoading: boolean
  error: string | null
}

export const useApiKlines = (): UseApiKlinesReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchKlines = async (
    symbol: string,
    interval: string,
    limit: number = 500
  ): Promise<any[] | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<any[]>(API_CONFIG.ENDPOINTS.KLINES, {
        params: { symbol, interval, limit }
      })

      if (Array.isArray(response.data)) {
        return response.data
      } else {
        setError('No klines data available')
        return null
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch klines'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    fetchKlines,
    isLoading,
    error
  }
}
