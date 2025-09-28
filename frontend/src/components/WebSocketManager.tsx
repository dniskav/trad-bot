import React, { useCallback, useContext, useEffect, useState } from 'react'
import { useWebSocketConnection } from '../contexts/WebSocketConnectionContext'
import { WebSocketContext } from '../contexts/WebSocketContext'
import { useBinanceSocket } from '../hooks/useBinanceSocket'

/**
 * WebSocketManager - Componente invisible que maneja las conexiones WebSocket
 *
 * Responsabilidades:
 * - Manejar conexión al servidor (useSocket)
 * - Manejar conexión a Binance (useBinanceSocket)
 * - Actualizar estados de conexión en el contexto
 * - Procesar mensajes y enviarlos al contexto de datos
 *
 * NO renderiza nada (return null)
 * Aísla los re-renders causados por los WebSockets
 */
const WebSocketManager: React.FC = () => {
  // Contexto para datos de mensajes
  const ctx = useContext(WebSocketContext)

  // Contexto para estados de conexión
  const { updateServerConnection, updateBinanceConnection } = useWebSocketConnection()

  // Hook para conexión al servidor - TEMPORALMENTE DESACTIVADO PARA DIAGNÓSTICO
  // const socket = useSocket({
  //   url: 'ws://127.0.0.1:8200/ws?interval=1m',
  //   autoConnect: true, // Conectar automáticamente
  //   reconnectInterval: 3000,
  //   maxReconnectAttempts: 5,
  //   onMessage: (data) => {
  //     // Actualizar contexto con mensaje recibido
  //     if (ctx) {
  //       ctx.addMessage('received', { ...data, __source: 'server' })
  //     }
  //   },
  //   onOpen: () => {
  //     // Actualizar contexto de conexión
  //     updateServerConnection({ isConnected: true, isConnecting: false, error: null })
  //   },
  //   onClose: () => {
  //     // Actualizar contexto de conexión
  //     updateServerConnection({ isConnected: false, isConnecting: false })
  //   },
  //   onError: (error) => {
  //     // Actualizar contexto de conexión
  //     updateServerConnection({ error: `Error: ${error.type}`, isConnecting: false })
  //   }
  // })

  // Hook para conexión a Binance - ACTIVADO CON INTERVALO DINÁMICO
  const [currentInterval, setCurrentInterval] = useState('1m')
  const binanceSocket = useBinanceSocket({ symbol: 'dogeusdt', interval: currentInterval })

  // Función para cambiar el intervalo del WebSocket
  const changeInterval = useCallback(
    (newInterval: string) => {
      console.log(`🔄 Cambiando intervalo del WebSocket: ${currentInterval} → ${newInterval}`)
      setCurrentInterval(newInterval)
    },
    [] // Remover currentInterval de las dependencias para evitar loops
  )

  // Exponer la función de cambio de intervalo al contexto
  useEffect(() => {
    if (ctx) {
      ctx.changeInterval = changeInterval
    }
  }, [changeInterval]) // Remover ctx de las dependencias para evitar loops

  // Actualizar estado de conexión Binance
  useEffect(() => {
    updateBinanceConnection({
      isConnected: binanceSocket.isConnected,
      isConnecting: binanceSocket.isConnecting,
      error: binanceSocket.error
    })
  }, [
    binanceSocket.isConnected,
    binanceSocket.isConnecting,
    binanceSocket.error,
    updateBinanceConnection
  ])

  // Procesar mensajes de Binance y enviarlos al contexto
  useEffect(() => {
    if (!ctx || !binanceSocket.lastMessage) return

    const msg = binanceSocket.lastMessage
    if (msg.type === 'binance.kline') {
      ctx.addMessage('received', {
        type: 'candles',
        data: { kline: msg.data },
        __source: 'binance'
      })
    } else if (msg.type === 'binance.bookTicker') {
      const price = Number(msg.data?.a || msg.data?.b || 0)
      ctx.addMessage('received', {
        type: 'price_update',
        data: { price },
        __source: 'binance'
      })
    }
  }, [binanceSocket.lastMessage]) // Remover ctx de las dependencias para evitar loops

  // Componente invisible - no renderiza nada
  return null
}

export default WebSocketManager
