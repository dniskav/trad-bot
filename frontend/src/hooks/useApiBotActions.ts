import { useCallback, useState } from 'react'
import API_CONFIG from '../config/api'
import apiClient from '../services/apiClient'

interface BotActionResponse {
  status: string
  message: string
}

interface UseApiBotActionsReturn {
  startBot: (botName: string, syntheticMode?: boolean) => Promise<boolean>
  stopBot: (botName: string) => Promise<boolean>
  updateBotConfig: (botName: string, configData: Record<string, any>) => Promise<boolean>
  isLoading: boolean
  error: string | null
}

export const useApiBotActions = (): UseApiBotActionsReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const startBot = useCallback(
    async (botName: string, syntheticMode: boolean = true): Promise<boolean> => {
      setIsLoading(true)
      setError(null)

      try {
        console.log(
          `🔄 useApiBotActions: Starting bot ${botName} in ${
            syntheticMode ? 'synthetic' : 'real'
          } mode...`
        )

        const response = await apiClient.post<BotActionResponse>(
          API_CONFIG.ENDPOINTS.BOT_START(botName),
          {},
          {
            params: {
              synthetic_mode: syntheticMode
            }
          }
        )

        if (response.data.status === 'success') {
          console.log(`✅ useApiBotActions: Bot ${botName} started successfully`)
          return true
        } else {
          setError(response.data.message || 'Failed to start bot')
          return false
        }
      } catch (err: any) {
        const errorMessage = err.response?.data?.message || err.message || 'Failed to start bot'
        setError(errorMessage)
        console.error(`❌ useApiBotActions: Error starting bot ${botName}:`, errorMessage)
        return false
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  const stopBot = useCallback(async (botName: string): Promise<boolean> => {
    setIsLoading(true)
    setError(null)

    try {
      console.log(`🔄 useApiBotActions: Stopping bot ${botName}...`)

      const response = await apiClient.post<BotActionResponse>(
        API_CONFIG.ENDPOINTS.BOT_STOP(botName)
      )

      if (response.data.status === 'success') {
        console.log(`✅ useApiBotActions: Bot ${botName} stopped successfully`)
        return true
      } else {
        setError(response.data.message || 'Failed to stop bot')
        return false
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to stop bot'
      setError(errorMessage)
      console.error(`❌ useApiBotActions: Error stopping bot ${botName}:`, errorMessage)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateBotConfig = useCallback(
    async (botName: string, configData: Record<string, any>): Promise<boolean> => {
      setIsLoading(true)
      setError(null)

      try {
        console.log(`🔄 useApiBotActions: Updating config for bot ${botName}:`, configData)

        const response = await apiClient.put<BotActionResponse>(
          API_CONFIG.ENDPOINTS.BOT_CONFIG(botName),
          configData
        )

        if (response.data.status === 'success') {
          console.log(`✅ useApiBotActions: Bot ${botName} config updated successfully`)
          return true
        } else {
          setError(response.data.message || 'Failed to update bot config')
          return false
        }
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.message || err.message || 'Failed to update bot config'
        setError(errorMessage)
        console.error(`❌ useApiBotActions: Error updating bot config ${botName}:`, errorMessage)
        return false
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return {
    startBot,
    stopBot,
    updateBotConfig,
    isLoading,
    error
  }
}
