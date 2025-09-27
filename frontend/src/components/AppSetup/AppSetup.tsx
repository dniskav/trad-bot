import React from 'react'
import { useWebSocketEvents } from '../../eventBus'
import { ProgressBar } from '../ProgressBar'
import './styles.css'
import type { AppSetupProps } from './types'

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  // Escuchar eventos de Binance WebSocket
  const binanceEvents = useWebSocketEvents('binance', {
    enableLogs: true,
    keepHistory: false
  })

  // Console.log de eventos Binance
  React.useEffect(() => {
    if (binanceEvents.lastEvent) {
      console.log(
        '🔗 Binance WebSocket:',
        binanceEvents.lastEvent.type,
        binanceEvents.lastEvent.data
      )
    }
  }, [binanceEvents.lastEvent])

  // Estados reales basados en eventos
  // const binanceConnected = binanceEvents.lastEvent?.type === 'ws:binance:connected'
  const binanceConnected = true
  const binanceConnecting =
    !binanceEvents.lastEvent || binanceEvents.lastEvent.type === 'ws:binance:disconnected'
  const binanceError =
    binanceEvents.lastEvent?.type === 'ws:binance:error' ? 'WebSocket error' : null

  // Mostrar loader solo hasta que Binance esté conectado
  if (!binanceConnected) {
    return (
      <div className="app-setup-loader">
        {/* Icono animado */}
        <div className="app-setup-icon">🚀</div>

        {/* Título */}
        <div className="app-setup-title">Trading Bot</div>

        {/* Estado del WebSocket Binance */}
        <div className="app-setup-status">
          <span
            className={`app-setup-indicator ${binanceConnecting ? 'connecting' : ''}`}
            style={{
              backgroundColor: binanceConnecting
                ? '#f59e0b'
                : binanceConnected
                ? '#10b981'
                : binanceError
                ? '#ef4444'
                : '#6b7280'
            }}
          />
          {binanceError && 'Error de conexión a Binance'}
          {!binanceError && binanceConnecting && 'Conectando a Binance...'}
          {!binanceError && !binanceConnecting && !binanceConnected && 'Binance offline'}
        </div>

        {/* Barra de progreso */}
        <ProgressBar
          isConnected={binanceConnected}
          isConnecting={binanceConnecting}
          error={binanceError}
          setupComplete={binanceConnected}
        />

        {/* Botón para conectar */}
        {!binanceConnected && !binanceConnecting && (
          <button className="app-setup-button connect" onClick={() => window.location.reload()}>
            🔌 Conectar a Binance
          </button>
        )}
      </div>
    )
  }

  // Mostrar la aplicación cuando Binance esté conectado
  return <>{children}</>
}

export default AppSetup
