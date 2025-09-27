import React, { useEffect, useState } from 'react'
import { useWebSocketConnection } from '../../contexts/WebSocketConnectionContext'
import { ProgressBar } from '../ProgressBar'
import './styles.css'
import type { AppSetupProps } from './types'

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  const [setupComplete, setSetupComplete] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)

  // Contexto de conexión para estados
  const { server, binance } = useWebSocketConnection()

  // TEMPORAL: Simular conexión del servidor para diagnóstico
  const simulatedServer = { ...server, isConnected: true, isConnecting: false, error: null }

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
    if (simulatedServer.isConnected && !setupComplete && !setupError) {
      performInitialSetup()
    }
  }, [simulatedServer.isConnected, setupComplete, setupError])

  // Resetear setup si el WebSocket se desconecta (TEMPORALMENTE DESHABILITADO)
  // const hasReset = React.useRef(false)
  // useEffect(() => {
  //   if (!socket.isConnected && setupComplete && !hasReset.current) {
  //     hasReset.current = true
  //     setSetupComplete(false)
  //     setSetupError(null)
  //   }
  //   // Reset hasReset cuando se vuelve a conectar
  //   if (socket.isConnected) {
  //     hasReset.current = false
  //   }
  // }, [socket.isConnected, setupComplete])

  // Mostrar loader mientras se configura (solo una vez)
  if (!simulatedServer.isConnected || !setupComplete) {
    return (
      <div className="app-setup-loader">
        {/* Icono animado */}
        <div className="app-setup-icon">🚀</div>

        {/* Título */}
        <div className="app-setup-title">Trading Bot</div>

        {/* Estado del WebSocket */}
        <div className="app-setup-status">
          <span
            className={`app-setup-indicator ${simulatedServer.isConnecting ? 'connecting' : ''}`}
            style={{
              backgroundColor: simulatedServer.isConnecting
                ? '#f59e0b'
                : simulatedServer.isConnected
                ? '#10b981'
                : simulatedServer.error
                ? '#ef4444'
                : '#6b7280'
            }}
          />
          {simulatedServer.error && 'Error de conexión'}
          {!simulatedServer.error && simulatedServer.isConnecting && 'Conectando al servidor...'}
          {!simulatedServer.error &&
            simulatedServer.isConnected &&
            !setupComplete &&
            'Configurando aplicación...'}
          {!simulatedServer.error &&
            !simulatedServer.isConnecting &&
            !simulatedServer.isConnected &&
            'Offline'}
        </div>

        {/* Barra de progreso */}
        <ProgressBar
          isConnected={simulatedServer.isConnected}
          isConnecting={simulatedServer.isConnecting}
          error={simulatedServer.error}
          setupComplete={setupComplete}
        />

        {/* Botón para conectar */}
        {!simulatedServer.isConnected && !simulatedServer.isConnecting && (
          <button className="app-setup-button connect" onClick={() => window.location.reload()}>
            🔌 Conectar al Servidor
          </button>
        )}

        {/* Botón para desconectar */}
        {simulatedServer.isConnected && (
          <button className="app-setup-button disconnect" onClick={() => window.location.reload()}>
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
