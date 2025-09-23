import { useCallback, useEffect, useRef, useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface KlinesResponse {
  status: string
  data: any[]
}

interface UseApiKlinesReturn {
  fetchKlines: (symbol: string, interval: string, limit?: number) => Promise<void>
  data: any[] | null
  isLoading: boolean
  error: string | null
}

export const useApiKlines = (): UseApiKlinesReturn => {
  const [data, setData] = useState<any[] | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lastFetchTimeRef = useRef<number>(0)
  const isMountedRef = useRef(true)
  const currentParamsRef = useRef<{ symbol: string; interval: string; limit?: number } | null>(null)

  const fetchKlines = useCallback(async (symbol: string, interval: string, limit: number = 500) => {
    const now = Date.now()
    const MIN_FETCH_INTERVAL = 5000 // 5 seconds minimum between fetches

    // Prevent duplicate requests with same parameters
    if (now - lastFetchTimeRef.current < MIN_FETCH_INTERVAL) {
      console.log('🚫 useApiKlines: Skipping fetch - too soon')
      return
    }

    if (!isMountedRef.current) return

    setIsLoading(true)
    setError(null)
    lastFetchTimeRef.current = now
    currentParamsRef.current = { symbol, interval, limit }

    try {
      console.log('🔄 useApiKlines: Fetching klines data...')
      const response = await apiClient.get<any[]>(API_CONFIG.ENDPOINTS.KLINES, {
        params: {
          symbol,
          interval,
          limit
        }
      })

      if (isMountedRef.current) {
        if (Array.isArray(response.data) && response.data.length > 0) {
          setData(response.data)
          console.log('✅ useApiKlines: Klines data fetched successfully')
        } else {
          setError('No klines data available')
        }
      }
    } catch (err: any) {
      if (isMountedRef.current) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch klines'
        setError(errorMessage)
        console.error('❌ useApiKlines: Error fetching klines:', errorMessage)
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  // Initial fetch on mount
  useEffect(() => {
    // Don't auto-fetch on mount, wait for explicit call
    return () => {
      isMountedRef.current = false
    }
  }, [])

  return {
    fetchKlines,
    data,
    isLoading,
    error
  }
}
