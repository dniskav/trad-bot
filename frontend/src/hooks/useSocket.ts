import { useCallback, useEffect, useState } from 'react'

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

// Singleton para la instancia global del WebSocket
class WebSocketSingleton {
  private static instance: WebSocketSingleton
  private ws: WebSocket | null = null
  private isConnected: boolean = false
  private isConnecting: boolean = false
  private error: string | null = null
  private lastMessage: any = null
  private reconnectAttempts: number = 0
  private url: string = 'ws://127.0.0.1:8200/ws'
  private autoConnect: boolean = true
  private reconnectInterval: number = 3000
  private maxReconnectAttempts: number = 5
  private reconnectTimeoutRef: number | null = null
  private reconnectAttemptsRef: number = 0
  private callbacks: {
    onMessage?: (message: any) => void
    onOpen?: () => void
    onClose?: () => void
    onError?: (error: Event) => void
  } = {}

  private constructor() {}

  static getInstance(): WebSocketSingleton {
    if (!WebSocketSingleton.instance) {
      WebSocketSingleton.instance = new WebSocketSingleton()
    }
    return WebSocketSingleton.instance
  }

  // Configurar opciones (solo la primera vez)
  configure(options: UseSocketOptions = {}) {
    if (this.ws === null) {
      // Solo configurar si no hay conexión existente
      this.url = options.url || 'ws://127.0.0.1:8200/ws'
      this.autoConnect = options.autoConnect !== false
      this.reconnectInterval = options.reconnectInterval || 3000
      this.maxReconnectAttempts = options.maxReconnectAttempts || 5

      if (options.onMessage) this.callbacks.onMessage = options.onMessage
      if (options.onOpen) this.callbacks.onOpen = options.onOpen
      if (options.onClose) this.callbacks.onClose = options.onClose
      if (options.onError) this.callbacks.onError = options.onError
    }
  }

  // Agregar callbacks adicionales
  addCallbacks(callbacks: {
    onMessage?: (message: any) => void
    onOpen?: () => void
    onClose?: () => void
    onError?: (error: Event) => void
  }) {
    if (callbacks.onMessage) this.callbacks.onMessage = callbacks.onMessage
    if (callbacks.onOpen) this.callbacks.onOpen = callbacks.onOpen
    if (callbacks.onClose) this.callbacks.onClose = callbacks.onClose
    if (callbacks.onError) this.callbacks.onError = callbacks.onError
  }

  connect() {
    if (this.isConnecting || this.isConnected) {
      return
    }

    if (!window.WebSocket) {
      this.error = 'WebSocket no soportado por el navegador'
      return
    }

    try {
      this.isConnecting = true
      this.error = null

      console.log('🔌 WebSocketSingleton: Conectando a:', this.url)

      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        this.isConnected = true
        this.isConnecting = false
        this.error = null
        this.reconnectAttempts = 0
        this.reconnectAttemptsRef = 0

        if (this.callbacks.onOpen) {
          this.callbacks.onOpen()
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.lastMessage = message

          if (this.callbacks.onMessage) {
            this.callbacks.onMessage(message)
          }
        } catch (err) {
          console.error('❌ WebSocketSingleton: Error parseando mensaje:', err)
        }
      }

      this.ws.onclose = (event) => {
        this.isConnected = false
        this.isConnecting = false

        if (this.callbacks.onClose) {
          this.callbacks.onClose()
        }
      }

      this.ws.onerror = (event) => {
        if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
          return
        }

        if (
          this.ws &&
          (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CLOSED)
        ) {
          this.error = `Error de conexión WebSocket: ${event.type}`
          this.isConnecting = false
        }

        if (this.callbacks.onError) {
          this.callbacks.onError(event)
        }
      }
    } catch (err) {
      this.error = 'Error creando conexión WebSocket'
      this.isConnecting = false
    }
  }

  disconnect() {
    if (this.reconnectTimeoutRef) {
      clearTimeout(this.reconnectTimeoutRef)
      this.reconnectTimeoutRef = null
    }

    if (this.ws) {
      this.ws.close(1000, 'Desconexión intencional')
      this.ws = null
    }

    this.isConnected = false
    this.isConnecting = false
    this.reconnectAttempts = 0
    this.reconnectAttemptsRef = 0
  }

  send(message: string) {
    console.log('📤 WebSocketSingleton: send() llamado')

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message)
      console.log('📤 WebSocketSingleton: Mensaje enviado:', message)
    } else {
      console.warn('⚠️ WebSocketSingleton: No se puede enviar mensaje, WebSocket no está abierto')
    }
  }

  // Getters para el estado
  getConnectionState() {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      error: this.error,
      lastMessage: this.lastMessage,
      reconnectAttempts: this.reconnectAttempts
    }
  }
}

export const useSocket = (options: UseSocketOptions = {}): UseSocketReturn => {
  // Obtener la instancia singleton
  const socketSingleton = WebSocketSingleton.getInstance()

  // Estados locales para re-renderizar cuando cambie el estado del socket
  const [connectionState, setConnectionState] = useState(socketSingleton.getConnectionState())

  // Configurar el socket (solo la primera vez)
  useEffect(() => {
    socketSingleton.configure(options)
  }, []) // Solo ejecutar una vez

  // Agregar callbacks adicionales si se proporcionan
  useEffect(() => {
    if (options.onMessage || options.onOpen || options.onClose || options.onError) {
      socketSingleton.addCallbacks({
        onMessage: options.onMessage,
        onOpen: options.onOpen,
        onClose: options.onClose,
        onError: options.onError
      })
    }
  }, [options.onMessage, options.onOpen, options.onClose, options.onError])

  // Auto-connect cuando el componente se monta (solo si autoConnect es true)
  useEffect(() => {
    if (options.autoConnect !== false) {
      socketSingleton.connect()
    }
  }, [options.autoConnect])

  // Actualizar estado local cuando cambie el estado del socket
  useEffect(() => {
    const updateState = () => {
      const newState = socketSingleton.getConnectionState()
      setConnectionState((prevState) => {
        // Solo actualizar si realmente cambió el estado
        if (JSON.stringify(prevState) !== JSON.stringify(newState)) {
          return newState
        }
        return prevState
      })
    }

    // Crear un intervalo para verificar cambios de estado (menos frecuente)
    const interval = setInterval(updateState, 1000) // Cambiado de 100ms a 1000ms

    return () => clearInterval(interval)
  }, [])

  // Funciones que delegan al singleton
  const connect = useCallback(() => {
    socketSingleton.connect()
    setConnectionState(socketSingleton.getConnectionState())
  }, [])

  const disconnect = useCallback(() => {
    socketSingleton.disconnect()
    setConnectionState(socketSingleton.getConnectionState())
  }, [])

  const send = useCallback((message: string) => {
    socketSingleton.send(message)
  }, [])

  return {
    connect,
    disconnect,
    send,
    isConnected: connectionState.isConnected,
    isConnecting: connectionState.isConnecting,
    error: connectionState.error,
    lastMessage: connectionState.lastMessage,
    reconnectAttempts: connectionState.reconnectAttempts
  }
}
