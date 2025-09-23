import React, { createContext, useContext, useState } from 'react'

interface WebSocketMessage {
  id: string
  type: 'sent' | 'received'
  message: any
  timestamp: number
}

interface WebSocketContextType {
  // Estado de conexión
  isConnected: boolean
  isConnecting: boolean
  error: string | null

  // Mensajes
  messages: WebSocketMessage[]
  lastMessage: WebSocketMessage | null

  // Funciones para actualizar el estado
  updateConnectionState: (state: {
    isConnected?: boolean
    isConnecting?: boolean
    error?: string | null
  }) => void
  addMessage: (type: 'sent' | 'received', message: any) => void
  clearMessages: () => void

  // Estado en tiempo real de plugin bots
  pluginBotsRealtime: Record<string, any>
  setPluginBotsRealtime: (data: Record<string, any>) => void
}

export const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const useWebSocketContext = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider')
  }
  return context
}

interface WebSocketProviderProps {
  children: React.ReactNode
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  // console.log('🔌 WebSocketProvider: Componente montado') // Comentado para reducir spam

  // Estado de conexión
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Mensajes
  const [messages, setMessages] = useState<WebSocketMessage[]>([])
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  // Estado WS específico: plugin bots realtime
  const [pluginBotsRealtime, setPluginBotsRealtime] = useState<Record<string, any>>({})

  // Función para actualizar el estado de conexión
  const updateConnectionState = (state: {
    isConnected?: boolean
    isConnecting?: boolean
    error?: string | null
  }) => {
    console.log('🔄 WebSocketContext: Actualizando estado de conexión:', state)
    if (state.isConnected !== undefined) setIsConnected(state.isConnected)
    if (state.isConnecting !== undefined) setIsConnecting(state.isConnecting)
    if (state.error !== undefined) setError(state.error)
  }

  // Función para agregar mensajes
  const addMessage = (type: 'sent' | 'received', message: any) => {
    const newMessage: WebSocketMessage = {
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      message,
      timestamp: Date.now()
    }

    console.log('📨 WebSocketContext: Agregando mensaje:', newMessage)
    setMessages((prev) => [...prev, newMessage])
    setLastMessage(newMessage)
  }

  // Función para limpiar mensajes
  const clearMessages = () => {
    console.log('🗑️ WebSocketContext: Limpiando mensajes')
    setMessages([])
    setLastMessage(null)
  }

  const value: WebSocketContextType = {
    // Estado de conexión
    isConnected,
    isConnecting,
    error,

    // Mensajes
    messages,
    lastMessage,

    // Funciones
    updateConnectionState,
    addMessage,
    clearMessages,

    // Realtime plugin bots
    pluginBotsRealtime,
    setPluginBotsRealtime
  }

  // console.log('🔌 WebSocketProvider: Renderizando con value:', value) // Comentado para reducir spam
  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}
