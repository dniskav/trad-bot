import { useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface StrategiesListResponse {
  strategies: any[]
  total: number
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
      // v0.2: read loaded strategies from server
      const response = await apiClient.get<StrategiesListResponse>(
        API_CONFIG.ENDPOINTS.STRATEGIES_LOADED
      )

      if (response.data && Array.isArray(response.data.strategies)) {
        // Map server strategies directly (avoid fabricating values)
        return response.data.strategies.map((s: any) => ({
          name: s.name,
          description: s.description,
          version: s.version,
          author: s.author,
          is_active: s.status === 'ACTIVE',
          positions_count: 0,
          last_signal: s.last_signal ?? null,
          start_time: s.started_at ?? null,
          uptime_seconds: null,
          uptime_formatted: null,
          config: {
            symbol: s.symbol,
            interval: s.interval
          },
          bot_description: s.description
        }))
      }

      setError('Invalid response format')
      return null
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
