import { useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface BotsResponse {
  status: string
  data: any[]
}

interface UseApiBotsReturn {
  fetchBots: () => Promise<any[] | null>
  isLoading: boolean
  error: string | null
}

export const useApiBots = (): UseApiBotsReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchBots = async (): Promise<any[] | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<BotsResponse>(API_CONFIG.ENDPOINTS.BOTS)

      if (response.data && typeof response.data === 'object') {
        if (response.data.data && Array.isArray(response.data.data)) {
          return response.data.data
        } else if (Array.isArray(response.data)) {
          return response.data
        } else {
          setError('Invalid response format')
          return null
        }
      } else {
        setError('Invalid response format')
        return null
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch bots'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    fetchBots,
    isLoading,
    error
  }
}
