import { useCallback, useRef, useState } from 'react'

interface UseSocketOptions {
  url?: string
  autoConnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
  onMessage?: (message: any) => void
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: Event) => void
}

interface UseSocketReturn {
  connect: () => void
  disconnect: () => void
  send: (message: string) => void
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: any
  reconnectAttempts: number
}

export const useSocket = (options: UseSocketOptions = {}): UseSocketReturn => {
  const {
    url = 'ws://localhost:3000/ws',
    // autoConnect = true, // Deshabilitado temporalmente
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onOpen,
    onClose,
    onError
  } = options

  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const connect = useCallback(() => {
    if (isConnecting || isConnected) {
      console.log('⚠️ useSocket: Ya conectando o conectado, saltando conexión')
      return
    }

    // Verificar si el navegador soporta WebSocket
    if (!window.WebSocket) {
      console.error('❌ useSocket: WebSocket no soportado por el navegador')
      setError('WebSocket no soportado por el navegador')
      return
    }

    try {
      setIsConnecting(true)
      setError(null)

      console.log('🔌 useSocket: Conectando a:', url)

      const ws = new WebSocket(url)
      wsRef.current = ws

      console.log('🔌 useSocket: WebSocket creado, readyState:', ws.readyState)

      ws.onopen = () => {
        console.log('✅ useSocket: WebSocket conectado')
        setIsConnected(true)
        setIsConnecting(false)
        setError(null)
        setReconnectAttempts(0)
        reconnectAttemptsRef.current = 0

        if (onOpen) {
          onOpen()
        }
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('📨 useSocket: Mensaje recibido:', message)
          setLastMessage(message)

          if (onMessage) {
            onMessage(message)
          }
        } catch (err) {
          console.error('❌ useSocket: Error parseando mensaje:', err)
        }
      }

      ws.onclose = (event) => {
        console.log('🔌 useSocket: WebSocket desconectado:', event.code, event.reason)
        setIsConnected(false)
        setIsConnecting(false)

        if (onClose) {
          onClose()
        }

        // Auto-reconnect deshabilitado temporalmente para evitar bucles
        console.log('🔌 useSocket: WebSocket cerrado, sin reconexión automática')

        // TODO: Implementar reconexión manual cuando sea necesario
        // if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts && !error) {
        //   reconnectAttemptsRef.current++
        //   setReconnectAttempts(reconnectAttemptsRef.current)
        //   console.log(`🔄 useSocket: Intentando reconectar (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`)
        //   reconnectTimeoutRef.current = window.setTimeout(() => {
        //     connect()
        //   }, reconnectInterval)
        // } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
        //   console.error('❌ useSocket: Máximo de intentos de reconexión alcanzado')
        //   setError('Máximo de intentos de reconexión alcanzado')
        // }
      }

      ws.onerror = (event) => {
        console.error('❌ useSocket: Error de WebSocket:', event)
        console.error('❌ useSocket: readyState:', ws.readyState)

        // No establecer error si el WebSocket está en estado de verificación
        if (ws.readyState === WebSocket.CONNECTING) {
          console.log('⚠️ useSocket: En estado CONNECTING, no es un error real')
          return
        }

        // Solo establecer error si el WebSocket está en estado OPEN o CLOSED
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CLOSED) {
          console.log('⚠️ useSocket: Error real detectado')
          setError(`Error de conexión WebSocket: ${event.type}`)
          setIsConnecting(false)
        }

        if (onError) {
          onError(event)
        }
      }
    } catch (err) {
      console.error('❌ useSocket: Error creando WebSocket:', err)
      setError('Error creando conexión WebSocket')
      setIsConnecting(false)
    }
  }, [
    url,
    isConnecting,
    isConnected,
    maxReconnectAttempts,
    reconnectInterval,
    onMessage,
    onOpen,
    onClose,
    onError
  ])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Desconexión intencional')
      wsRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
    setReconnectAttempts(0)
    reconnectAttemptsRef.current = 0
  }, [])

  const send = useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message)
      console.log('📤 useSocket: Mensaje enviado:', message)
    } else {
      console.warn('⚠️ useSocket: No se puede enviar mensaje, WebSocket no está abierto')
    }
  }, [])

  // Auto-connect deshabilitado temporalmente para evitar bucles
  // useEffect(() => {
  //   if (autoConnect) {
  //     connect()
  //   }
  //   return () => {
  //     disconnect()
  //   }
  // }, [autoConnect])

  return {
    connect,
    disconnect,
    send,
    isConnected,
    isConnecting,
    error,
    lastMessage,
    reconnectAttempts
  }
}
