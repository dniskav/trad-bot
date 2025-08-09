import React, { createContext, useContext, useEffect, useRef, useState } from 'react'

interface WebSocketContextType {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: any
  reconnect: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
  url?: string
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({
  children,
  url = 'ws://localhost:8000/ws'
}) => {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<any>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = () => {
    if (isConnecting || isConnected) {
      return
    }

    try {
      setIsConnecting(true)
      setError(null)

      console.log('🔌 Conectando a WebSocket:', url)
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('✅ WebSocket conectado')
        setIsConnected(true)
        setIsConnecting(false)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('📨 Mensaje WebSocket recibido:', message)
          setLastMessage(message)
        } catch (err) {
          console.error('❌ Error parseando mensaje WebSocket:', err)
        }
      }

      ws.onclose = (event) => {
        console.log('🔌 WebSocket desconectado:', event.code, event.reason)
        setIsConnected(false)
        setIsConnecting(false)

        // Auto-reconnect after 3 seconds
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect()
        }, 3000)
      }

      ws.onerror = (event) => {
        console.error('❌ Error de WebSocket:', event)
        setError('Error de conexión WebSocket')
        setIsConnecting(false)
      }
    } catch (err) {
      console.error('❌ Error creando WebSocket:', err)
      setError('Error creando conexión WebSocket')
      setIsConnecting(false)
    }
  }

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
  }

  const reconnect = () => {
    console.log('🔄 Reconectando WebSocket...')
    disconnect()

    // Small delay before reconnecting
    setTimeout(() => {
      connect()
    }, 1000)
  }

  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [url])

  const value: WebSocketContextType = {
    isConnected,
    isConnecting,
    error,
    lastMessage,
    reconnect
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}
