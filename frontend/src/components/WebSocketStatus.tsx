import React from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'

const WebSocketStatus: React.FC = () => {
  const { isConnected, isConnecting, error, reconnect } = useWebSocketContext()

  const getStatusColor = () => {
    if (isConnected) return '#4ade80' // green
    if (isConnecting) return '#fbbf24' // yellow
    if (error) return '#f87171' // red
    return '#9ca3af' // gray
  }

  const getStatusText = () => {
    if (isConnected) return 'Conectado'
    if (isConnecting) return 'Conectando...'
    if (error) return 'Error'
    return 'Desconectado'
  }

  const getStatusIcon = () => {
    if (isConnected) return '🟢'
    if (isConnecting) return '🟡'
    if (error) return '🔴'
    return '⚪'
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(10px)',
        border: `2px solid ${getStatusColor()}`,
        borderRadius: '12px',
        padding: '12px 16px',
        fontSize: '14px',
        color: 'white',
        zIndex: 1000,
        minWidth: '140px',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)'
      }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
        <span style={{ fontSize: '16px' }}>{getStatusIcon()}</span>
        <span style={{ fontWeight: 'bold' }}>WebSocket</span>
      </div>

      <div
        style={{
          fontSize: '12px',
          color: getStatusColor(),
          fontWeight: '500'
        }}>
        {getStatusText()}
      </div>

      {error && (
        <button
          onClick={reconnect}
          style={{
            fontSize: '11px',
            padding: '4px 8px',
            backgroundColor: 'rgba(255, 255, 255, 0.2)',
            color: 'white',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            borderRadius: '6px',
            cursor: 'pointer',
            marginTop: '6px',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.3)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'
          }}>
          🔄 Reconectar
        </button>
      )}
    </div>
  )
}

export default WebSocketStatus
