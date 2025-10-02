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
        // ⚠️ FIX: Ya NO usar HTTP para position_change genérico
        console.log('🔔 Generic position_change event ignored (no fields/id) - updates via WebSocket')
        return
      }
      
      if (t === SocketMsg.POSITION_OPENED) {
        // ⚠️ FIX: Actualizar lista localmente SIN HTTP cuando se abre una posición
        console.log('🔔 POSITION_OPENED event:', msg.positionId, '- Adding to local state (NO HTTP)')
        if (msg.position && msg.positionId) {
          setPositions((prev) => [...prev, msg.position])
        }
        return
      }
      
      if (t === SocketMsg.POSITION_CLOSED) {
        // ⚠️ FIX: Remover de lista localmente SIN HTTP cuando se cierra una posición
        console.log('🔔 POSITION_CLOSED event:', msg.positionId, '- Removing from local state (NO HTTP)')
        if (msg.positionId) {
          setPositions((prev) => prev.filter(p => p.positionId !== msg.positionId))
        }
        return
      }
    }

    eventBus.on(EventType.WS_SERVER_POSITIONS, handler)
    return () => eventBus.off(EventType.WS_SERVER_POSITIONS, handler)
  }, []) // ⚠️ FIJO: Sin dependencias para evitar ciclo infinito

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
          const qty =
            Math.abs(
              parseFloat(((p as any).positionAmt ?? (p as any).quantity ?? '0') as string)
            ) || 0
          const entry = parseFloat((p as any).entryPrice) || 0
          // Determine side robustly: prefer positionSide, then side, then sign of positionAmt
          const sideRaw =
            ((p as any).positionSide ||
              (p as any).side ||
              (((p as any).positionAmt ?? 0) < 0 ? 'SELL' : 'BUY')) + ''
          const side = sideRaw.toUpperCase()
          const gross = side === 'SELL' ? (entry - price) * qty : (price - entry) * qty
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
  }, []) // ⚠️ FIJO: Solo una vez al montar

  // WebSocket functionality removed - using only API data

  // Función para actualizar posiciones manualmente
  const refreshPositions = useCallback(() => {
    fetchActivePositions()
  }, []) // ⚠️ FIJO: Sin dependencias

  return {
    positions,
    loading,
    error,
    refreshPositions
  }
}
