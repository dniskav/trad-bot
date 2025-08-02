import { useState, useEffect, useRef } from 'react'

interface WebSocketMessage {
  type: 'position' | 'price' | 'trade'
  data: any
}

export const useWebSocket = (url: string = 'ws://localhost:8000/ws') => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 3

  const connect = () => {
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)
        reconnectAttempts.current = 0
        console.log('WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          setLastMessage(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket disconnected')

        // Auto-reconnect logic
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++
          console.log(
            `Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})...`
          )
          setTimeout(connect, 1000 * reconnectAttempts.current)
        } else {
          setError('Failed to reconnect after 3 attempts')
        }
      }

      ws.onerror = (event) => {
        setError('WebSocket error occurred')
        console.error('WebSocket error:', event)
      }
    } catch (err) {
      setError('Failed to create WebSocket connection')
      console.error('WebSocket connection error:', err)
    }
  }

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }

  const sendMessage = (message: any) => {
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify(message))
    }
  }

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [url])

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    connect,
    disconnect
  }
}
