import { useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface TradingHistoryResponse {
  status: string
  data?: {
    items?: any[]
    history?: any[]
  }
}

interface UseApiTradingHistoryReturn {
  fetchTradingHistory: (page?: number, pageSize?: number) => Promise<any[] | null>
  isLoading: boolean
  error: string | null
}

export const useApiTradingHistory = (): UseApiTradingHistoryReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTradingHistory = async (
    pageNum: number = 1,
    pageSizeNum: number = 10000
  ): Promise<any[] | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<TradingHistoryResponse>(
        API_CONFIG.ENDPOINTS.TRADING_HISTORY,
        {
          params: { page: pageNum, page_size: pageSizeNum }
        }
      )

      if (response.data && typeof response.data === 'object') {
        if (response.data.status === 'success') {
          const payload: any = response.data.data || {}
          const items = Array.isArray(payload.items)
            ? payload.items
            : Array.isArray(payload.history)
            ? payload.history
            : null
          return items
        }
        setError('Failed to fetch trading history')
        return null
      } else {
        setError('Invalid response format')
        return null
      }
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || err.message || 'Failed to fetch trading history'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    fetchTradingHistory,
    isLoading,
    error
  }
}
