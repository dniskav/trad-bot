import React, { useContext, useEffect, useState } from 'react'
import { WebSocketContext } from '../../contexts/WebSocketContext'
import { useBinanceSocket } from '../../hooks/useBinanceSocket'
import { useSocket } from '../../hooks/useSocket'
import { ProgressBar } from '../ProgressBar'
import './styles.css'
import type { AppSetupProps } from './types'

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  const [setupComplete, setSetupComplete] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)

  // Contexto WebSocket
  const ctx = useContext(WebSocketContext)

  // Hook useSocket para manejar la conexión WebSocket
  const socket = useSocket({
    url: 'ws://127.0.0.1:8200/ws?interval=1m',
    autoConnect: true, // Conectar automáticamente
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    onMessage: (data) => {
      // Actualizar contexto con mensaje recibido
      if (ctx) {
        ctx.addMessage('received', { ...data, __source: 'server' })
      }
    },
    onOpen: () => {
      // Actualizar contexto con estado de conexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: true, isConnecting: false, error: null })
      }
    },
    onClose: () => {
      // Actualizar contexto con estado de desconexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: false, isConnecting: false })
      }
    },
    onError: (error) => {
      // Actualizar contexto con error
      if (ctx) {
        ctx.updateConnectionState({ error: `Error: ${error.type}`, isConnecting: false })
      }
    }
  })

  // Hook para Binance WS directo (kline + bookTicker)
  const binance = useBinanceSocket({ symbol: 'dogeusdt', interval: '1m' })

  // Publicar mensajes de Binance en el contexto con formato unificado
  useEffect(() => {
    if (!ctx || !binance.lastMessage) return

    const msg = binance.lastMessage
    if (msg.type === 'binance.kline') {
      ctx.addMessage('received', {
        type: 'candles',
        data: { kline: msg.data },
        __source: 'binance'
      })
    } else if (msg.type === 'binance.bookTicker') {
      const price = Number(msg.data?.a || msg.data?.b || 0)
      ctx.addMessage('received', { type: 'price_update', data: { price }, __source: 'binance' })
    }
  }, [binance.lastMessage])

  // Actualizar estado visual de conexión Binance
  useEffect(() => {
    if (!ctx) return
    ctx.updateBinanceConnectionState({
      isConnected: binance.isConnected,
      isConnecting: binance.isConnecting,
      error: binance.error
    })
  }, [binance.isConnected, binance.isConnecting, binance.error])

  // Función para iniciar la conexión manualmente
  const handleConnect = () => {
    socket.connect()
  }

  // Función para hacer las peticiones iniciales al servidor
  const performInitialSetup = async () => {
    try {
      // Aquí puedes agregar todas las peticiones iniciales necesarias
      // Por ejemplo:
      // - Cargar configuración del usuario
      // - Verificar permisos
      // - Cargar datos iniciales
      // - etc.

      setSetupComplete(true)
    } catch (err) {
      setSetupError('Error al configurar la aplicación')
    }
  }

  // Efecto para manejar el setup cuando el WebSocket esté listo
  useEffect(() => {
    if (socket.isConnected && !setupComplete && !setupError) {
      performInitialSetup()
    }
  }, [socket.isConnected, setupComplete, setupError])

  // Resetear setup si el WebSocket se desconecta (SOLO UNA VEZ)
  const hasReset = React.useRef(false)
  useEffect(() => {
    if (!socket.isConnected && setupComplete && !hasReset.current) {
      hasReset.current = true
      setSetupComplete(false)
      setSetupError(null)
    }
  }, [socket.isConnected, setupComplete])

  // Mostrar loader mientras se configura (solo una vez)
  if (!socket.isConnected || !setupComplete) {
    return (
      <div className="app-setup-loader">
        {/* Icono animado */}
        <div className="app-setup-icon">🚀</div>

        {/* Título */}
        <div className="app-setup-title">Trading Bot</div>

        {/* Estado del WebSocket */}
        <div className="app-setup-status">
          <span
            className={`app-setup-indicator ${socket.isConnecting ? 'connecting' : ''}`}
            style={{
              backgroundColor: socket.isConnecting
                ? '#f59e0b'
                : socket.isConnected
                ? '#10b981'
                : socket.error
                ? '#ef4444'
                : '#6b7280'
            }}
          />
          {socket.error && 'Error de conexión'}
          {!socket.error && socket.isConnecting && 'Conectando al servidor...'}
          {!socket.error && socket.isConnected && !setupComplete && 'Configurando aplicación...'}
          {!socket.error && !socket.isConnecting && !socket.isConnected && 'Offline'}
        </div>

        {/* Barra de progreso */}
        <ProgressBar
          isConnected={socket.isConnected}
          isConnecting={socket.isConnecting}
          error={socket.error}
          setupComplete={setupComplete}
        />

        {/* Botón para conectar */}
        {!socket.isConnected && !socket.isConnecting && (
          <button className="app-setup-button connect" onClick={handleConnect}>
            🔌 Conectar al Servidor
          </button>
        )}

        {/* Botón para desconectar */}
        {socket.isConnected && (
          <button className="app-setup-button disconnect" onClick={() => socket.disconnect()}>
            🛑 Desconectar
          </button>
        )}

        {/* Mensaje de error */}
        {setupError && <div className="app-setup-error">{setupError}</div>}
      </div>
    )
  }

  // Mostrar la aplicación cuando todo esté listo
  return <>{children}</>
}

export default AppSetup
