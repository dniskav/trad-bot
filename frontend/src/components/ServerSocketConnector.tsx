import React, { useEffect } from 'react'
import { eventBus } from '../eventBus/eventBus'
import { EventType, SocketMsg } from '../eventBus/types'
import { useWebSocket } from '../hooks/useWebSocket'

/**
 * Invisible component that ensures a persistent WebSocket connection
 * to the server via Vite proxy (ws(s)://<host>/ws).
 */
const ServerSocketConnector: React.FC = () => {
  const onMessage = (message: any) => {
    const t = (message && message.type) as string
    // Debug: ver todo lo que llega por el WS del server
    // console.log('🌐 Server WS message:', t, message)
    if (t === SocketMsg.ACCOUNT_BALANCE_UPDATE) {
      eventBus.emit(EventType.WS_SERVER_ACCOUNT_BALANCE, message)
    } else if (
      t === SocketMsg.POSITION_CHANGE ||
      t === SocketMsg.POSITION_OPENED ||
      t === SocketMsg.POSITION_CLOSED
    ) {
      eventBus.emit(EventType.WS_SERVER_POSITIONS, message)
    } else if (message && message.channel === 'strategies') {
      eventBus.emit(EventType.WS_SERVER_STRATEGIES, message)
    } else if (t === SocketMsg.KLINE) {
      eventBus.emit(EventType.WS_BINANCE_KLINE, message)
    } else if (t === SocketMsg.BOOK_TICKER) {
      eventBus.emit(EventType.WS_BINANCE_BOOK_TICKER, message)
    }
  }

  const { isConnected, isConnecting, error, reconnect } = useWebSocket(undefined, (message) => {
    onMessage(message)
  })

  useEffect(() => {
    if (error) {
      // Attempt a delayed reconnect on error
      const t = setTimeout(reconnect, 2000)
      return () => clearTimeout(t)
    }
  }, [error, reconnect])

  // No UI rendered
  return null
}

export default ServerSocketConnector
