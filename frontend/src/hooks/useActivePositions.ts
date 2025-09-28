import { useCallback, useEffect, useState } from 'react'
import { API_CONFIG } from '../config/api'
import apiClient from '../services/apiClient'

const log = console

interface Position {
  positionId: string
  symbol: string
  initialMargin: string
  maintMargin: string
  unrealizedProfit: string
  positionInitialMargin: string
  openOrderInitialMargin: string
  leverage: string
  isolated: boolean
  entryPrice: string
  maxNotional: string
  bidNotional: string
  askNotional: string
  positionSide: string
  positionAmt: string
  updateTime: string
}

interface ActivePositionsResponse {
  success: boolean
  positions: Position[]
  count: number
}

export const useActivePositions = () => {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchActivePositions = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<ActivePositionsResponse>(
        `${API_CONFIG.ENDPOINTS.POSITIONS}/?status=open`
      )

      if (response.data.success) {
        setPositions(response.data.positions)
      } else {
        setError('Error al cargar posiciones')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Error de conexión'
      setError(errorMessage)
      console.error('Error fetching active positions:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Cargar posiciones al montar el componente
  useEffect(() => {
    fetchActivePositions()
  }, [fetchActivePositions])

  // WebSocket functionality removed - using only API data

  // Función para actualizar posiciones manualmente
  const refreshPositions = useCallback(() => {
    fetchActivePositions()
  }, [fetchActivePositions])

  return {
    positions,
    loading,
    error,
    refreshPositions
  }
}
