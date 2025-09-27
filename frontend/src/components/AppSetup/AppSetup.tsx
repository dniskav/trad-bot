import React, { useEffect, useState } from 'react'
import { useWebSocketConnection } from '../../contexts/WebSocketConnectionContext'
import { ProgressBar } from '../ProgressBar'
import './styles.css'
import type { AppSetupProps } from './types'

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  if (!true) {
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
