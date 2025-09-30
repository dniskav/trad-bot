import { useCallback, useEffect, useRef, useState } from 'react'
import { API_CONFIG } from '../config/api'
import { eventBus } from '../eventBus/eventBus'
import { EventType, SocketMsg } from '../eventBus/types'
import apiClient from '../services/apiClient'

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
  count?: number
  message?: string
}

export const useActivePositions = () => {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const positionsRef = useRef<Position[]>([])
  positionsRef.current = positions
  const debounceRef = useRef<number | null>(null)

  const fetchActivePositions = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      // Query open positions via server (supports /positions?status=open)
      const response = await apiClient.get<ActivePositionsResponse>(
        `${API_CONFIG.ENDPOINTS.POSITIONS}/?status=open`
      )

      if (response.data.success && Array.isArray(response.data.positions)) {
        setPositions(response.data.positions)
      } else {
        setError(response.data.message || 'Error al cargar posiciones')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Error de conexión'
      setError(errorMessage)
      console.error('Error fetching active positions:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // Subscribe to EventBus for server position events
  useEffect(() => {
    const handler = (msg: any) => {
      const t = (msg && msg.type) as string
      // Debug: inspeccionar mensajes del EventBus
      console.log('🛰️ WS_SERVER_POSITIONS event:', t, msg)
      if (t === SocketMsg.POSITION_CHANGE && msg.positionId && msg.fields) {
        console.log('↔️ Merging position_change into state', msg.positionId, msg.fields)
        setPositions((prev) =>
          prev.map((p) => (p.positionId === msg.positionId ? { ...p, ...msg.fields } : p))
        )
        return
      }
      if (t === SocketMsg.POSITION_CHANGE && (!msg.positionId || !msg.fields)) {
        // Algunos cambios no incluyen diff ni id; usar refetch como fallback
        console.log('🔁 Refetch due to generic position_change (no fields/id)')
        if (debounceRef.current) window.clearTimeout(debounceRef.current)
        debounceRef.current = window.setTimeout(() => {
          fetchActivePositions()
        }, 250)
        return
      }
      if (t === SocketMsg.POSITION_OPENED || t === SocketMsg.POSITION_CLOSED) {
        console.log('🔁 Refetch positions due to lifecycle event', t)
        if (debounceRef.current) window.clearTimeout(debounceRef.current)
        debounceRef.current = window.setTimeout(() => {
          fetchActivePositions()
        }, 250)
      }
    }

    eventBus.on(EventType.WS_SERVER_POSITIONS, handler)
    return () => eventBus.off(EventType.WS_SERVER_POSITIONS, handler)
  }, [fetchActivePositions])

  // Subscribe to Binance bookTicker to update PnL in real time on the client
  useEffect(() => {
    const handler = (msg: any) => {
      // Expected shape from server: { type: 'bookTicker', symbol: 'DOGEUSDT', bid: '...', ask: '...' }
      const bid = parseFloat(msg?.bid)
      const ask = parseFloat(msg?.ask)
      if (!isFinite(bid) || !isFinite(ask)) return
      const price = (bid + ask) / 2
      setPositions((prev) =>
        prev.map((p) => {
          // Long/short not fully supported here; we treat positionSide 'LONG' as long
          const qty = Math.abs(parseFloat(p.positionAmt)) || 0
          const entry = parseFloat(p.entryPrice) || 0
          const side = (p.positionSide || 'LONG').toUpperCase()
          const gross = side === 'SELL' ? (entry - price) * qty : (price - entry) * qty
          // Keep strings for compatibility
          return { ...p, unrealizedProfit: gross.toString() }
        })
      )
    }

    eventBus.on(EventType.WS_BINANCE_BOOK_TICKER, handler)
    return () => eventBus.off(EventType.WS_BINANCE_BOOK_TICKER, handler)
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
