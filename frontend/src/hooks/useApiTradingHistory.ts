import { useCallback, useEffect, useRef, useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface TradingHistoryResponse {
  status: string
  data: {
    items: any[]
    total: number
    page: number
    page_size: number
  }
}

interface UseApiTradingHistoryReturn {
  fetchTradingHistory: (page?: number, pageSize?: number) => Promise<void>
  data: any[] | null
  isLoading: boolean
  error: string | null
  total: number
  page: number
  pageSize: number
}

export const useApiTradingHistory = (): UseApiTradingHistoryReturn => {
  const [data, setData] = useState<any[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(1000)
  const lastFetchTimeRef = useRef<number>(0)
  const isMountedRef = useRef(true)

  const fetchTradingHistory = useCallback(
    async (pageNum: number = 1, pageSizeNum: number = 1000) => {
      const now = Date.now()
      const MIN_FETCH_INTERVAL = 10000 // 10 seconds minimum between fetches

      // Prevent duplicate requests
      if (now - lastFetchTimeRef.current < MIN_FETCH_INTERVAL) {
        console.log('🚫 useApiTradingHistory: Skipping fetch - too soon')
        return
      }

      if (!isMountedRef.current) return

      setIsLoading(true)
      setError(null)
      lastFetchTimeRef.current = now

      try {
        console.log('🔄 useApiTradingHistory: Fetching trading history...')
        const response = await apiClient.get<TradingHistoryResponse>(
          API_CONFIG.ENDPOINTS.TRADING_HISTORY,
          {
            params: {
              page: pageNum,
              page_size: pageSizeNum
            }
          }
        )

        if (isMountedRef.current) {
          if (response.data.status === 'success') {
            setData(response.data.data.items)
            setTotal(response.data.data.total)
            setPage(response.data.data.page)
            setPageSize(response.data.data.page_size)
            console.log('✅ useApiTradingHistory: Trading history fetched successfully')
          } else {
            setError('Failed to fetch trading history')
          }
        }
      } catch (err: any) {
        if (isMountedRef.current) {
          const errorMessage =
            err.response?.data?.message || err.message || 'Failed to fetch trading history'
          setError(errorMessage)
          console.error('❌ useApiTradingHistory: Error fetching trading history:', errorMessage)
        }
      } finally {
        if (isMountedRef.current) {
          setIsLoading(false)
        }
      }
    },
    []
  )

  // Initial fetch on mount
  useEffect(() => {
    fetchTradingHistory()

    return () => {
      isMountedRef.current = false
    }
  }, []) // Remove fetchTradingHistory dependency to prevent infinite loop

  return {
    fetchTradingHistory,
    data,
    isLoading,
    error,
    total,
    page,
    pageSize
  }
}
