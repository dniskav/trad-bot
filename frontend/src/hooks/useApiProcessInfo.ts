import API_CONFIG from '@config/api'
import apiClient from '@services/apiClient'
import { useState } from 'react'

interface ProcessInfoResponse {
  status: string
  data: any
}

interface UseApiProcessInfoReturn {
  fetchProcessInfo: () => Promise<any | null>
  isLoading: boolean
  error: string | null
}

export const useApiProcessInfo = (): UseApiProcessInfoReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchProcessInfo = async (): Promise<any | null> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<ProcessInfoResponse>(
        API_CONFIG.ENDPOINTS.BOT_PROCESS_INFO
      )

      if (response.data.status === 'success') {
        return response.data.data
      } else {
        setError('Failed to fetch process info')
        return null
      }
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || err.message || 'Failed to fetch process info'
      setError(errorMessage)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  return {
    fetchProcessInfo,
    isLoading,
    error
  }
}
