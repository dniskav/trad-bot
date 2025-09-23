import { useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface MarginInfoResponse {
  status: string
  data: any
}

interface UseApiMarginInfoReturn {
  fetchMarginInfo: () => Promise<any | null>
  isLoading: boolean
  error: string | null
}

export const useApiMarginInfo = (): UseApiMarginInfoReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMarginInfo = async (): Promise<any | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<MarginInfoResponse>(API_CONFIG.ENDPOINTS.MARGIN_INFO)

      if (response.data && typeof response.data === 'object') {
        if (response.data.data) {
          return response.data.data
        } else {
          return response.data
        }
      } else {
        setError('Invalid response format')
        return null
      }
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || err.message || 'Failed to fetch margin info'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    fetchMarginInfo,
    isLoading,
    error
  }
}
