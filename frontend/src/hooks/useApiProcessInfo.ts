import { useCallback, useEffect, useRef, useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface ProcessInfoResponse {
  status: string
  data: any
}

interface UseApiProcessInfoReturn {
  fetchProcessInfo: () => Promise<void>
  data: any | null
  isLoading: boolean
  error: string | null
}

export const useApiProcessInfo = (): UseApiProcessInfoReturn => {
  const [data, setData] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const lastFetchTimeRef = useRef<number>(0)
  const isMountedRef = useRef(true)

  const fetchProcessInfo = useCallback(async () => {
    const now = Date.now()
    const MIN_FETCH_INTERVAL = 10000 // 10 seconds minimum between fetches

    // Prevent duplicate requests
    if (now - lastFetchTimeRef.current < MIN_FETCH_INTERVAL) {
      console.log('🚫 useApiProcessInfo: Skipping fetch - too soon')
      return
    }

    if (!isMountedRef.current) return

    setIsLoading(true)
    setError(null)
    lastFetchTimeRef.current = now

    try {
      console.log('🔄 useApiProcessInfo: Fetching process info...')
      const response = await apiClient.get<ProcessInfoResponse>(
        API_CONFIG.ENDPOINTS.BOT_PROCESS_INFO
      )

      if (isMountedRef.current) {
        if (response.data.status === 'success') {
          setData(response.data.data)
          console.log('✅ useApiProcessInfo: Process info fetched successfully')
        } else {
          setError('Failed to fetch process info')
        }
      }
    } catch (err: any) {
      if (isMountedRef.current) {
        const errorMessage =
          err.response?.data?.message || err.message || 'Failed to fetch process info'
        setError(errorMessage)
        console.error('❌ useApiProcessInfo: Error fetching process info:', errorMessage)
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  // Initial fetch on mount
  useEffect(() => {
    fetchProcessInfo()

    return () => {
      isMountedRef.current = false
    }
  }, []) // Remove fetchProcessInfo dependency to prevent infinite loop

  return {
    fetchProcessInfo,
    data,
    isLoading,
    error
  }
}
