import { useEffect, useRef, useState } from 'react'
// Nota: la propagación por EventBus se hará desde los consumidores (p. ej., ServerSocketConnector)

interface UseWebSocketReturn {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  reconnect: () => void
}

export const useWebSocket = (
  // Route WS through Vite proxy: ws(s)://<host>/ws → proxied to backend 8200
  url: string = typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`
    : 'ws://127.0.0.1:3000/ws',
  onMessage?: (message: any) => void
): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = () => {
    if (isConnecting || isConnected) {
      return
    }

    try {
      setIsConnecting(true)
      setError(null)

      // console.log('🔌 Conectando a WebSocket:', url)
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
          // console.log('📨 Mensaje WebSocket recibido:', message) // Comentado para reducir spam
          if (onMessage) {
            onMessage(message)
          }
          // Dejar que el caller maneje la propagación (event bus u otro)
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

  return {
    isConnected,
    isConnecting,
    error,
    reconnect
  }
}
