import type { ReactNode } from 'react'
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
// Estados de conexión para WebSockets
interface WebSocketConnectionState {
  // Server WebSocket
  server: {
    isConnected: boolean
    isConnecting: boolean
    error: string | null
  }
  // Binance WebSocket
  binance: {
    isConnected: boolean
    isConnecting: boolean
    error: string | null
  }
}

// Acciones para actualizar estados de conexión
interface WebSocketConnectionActions {
  updateServerConnection: (state: Partial<WebSocketConnectionState['server']>) => void
  updateBinanceConnection: (state: Partial<WebSocketConnectionState['binance']>) => void
  resetConnections: () => void
}

// Contexto combinado
type WebSocketConnectionContextType = WebSocketConnectionState & WebSocketConnectionActions

// Crear contexto
const WebSocketConnectionContext = createContext<WebSocketConnectionContextType | undefined>(
  undefined
)

// Estado inicial
const initialState: WebSocketConnectionState = {
  server: {
    isConnected: false,
    isConnecting: false,
    error: null
  },
  binance: {
    isConnected: false,
    isConnecting: false,
    error: null
  }
}

// Provider del contexto
interface WebSocketConnectionProviderProps {
  children: ReactNode
}

export const WebSocketConnectionProvider: React.FC<WebSocketConnectionProviderProps> = ({
  children
}) => {
  const [connectionState, setConnectionState] = useState<WebSocketConnectionState>(initialState)

  // Actualizar estado del servidor
  const updateServerConnection = useCallback(
    (state: Partial<WebSocketConnectionState['server']>) => {
      setConnectionState((prev) => ({
        ...prev,
        server: { ...prev.server, ...state }
      }))
    },
    []
  )

  // Actualizar estado de Binance
  const updateBinanceConnection = useCallback(
    (state: Partial<WebSocketConnectionState['binance']>) => {
      setConnectionState((prev) => ({
        ...prev,
        binance: { ...prev.binance, ...state }
      }))
    },
    []
  )

  // Resetear todas las conexiones
  const resetConnections = useCallback(() => {
    setConnectionState(initialState)
  }, [])

  const value: WebSocketConnectionContextType = useMemo(
    () => ({
      ...connectionState,
      updateServerConnection,
      updateBinanceConnection,
      resetConnections
    }),
    [connectionState, updateServerConnection, updateBinanceConnection, resetConnections]
  )

  return (
    <WebSocketConnectionContext.Provider value={value}>
      {children}
    </WebSocketConnectionContext.Provider>
  )
}

// Hook para usar el contexto
export const useWebSocketConnection = (): WebSocketConnectionContextType => {
  const context = useContext(WebSocketConnectionContext)
  if (context === undefined) {
    throw new Error('useWebSocketConnection must be used within a WebSocketConnectionProvider')
  }
  return context
}

export default WebSocketConnectionContext
