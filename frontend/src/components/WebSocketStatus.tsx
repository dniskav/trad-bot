import React from 'react'
import { useWebSocketContext } from '../contexts/WebSocketContext'

const WebSocketStatus: React.FC = () => {
  const { isConnected, isConnecting, error } = useWebSocketContext()

  const getStatusIcon = () => {
    if (isConnected) return '🟢'
    if (isConnecting) return '🟡'
    if (error) return '🔴'
    return '⚪'
  }

  const getBorderColor = () => {
    if (isConnected) return '#10b981' // green
    if (isConnecting) return '#f59e0b' // yellow
    if (error) return '#ef4444' // red
    return '#6b7280' // gray
  }

  return (
    <div
      style={{
        backgroundColor: 'transparent',
        backdropFilter: 'none',
        border: `2px solid ${getBorderColor()}`,
        borderRadius: '4px',
        padding: '0',
        fontSize: '0.5rem',
        color: 'white',
        zIndex: 1000,
        minWidth: 'auto',
        boxShadow: 'none',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '3px'
      }}>
      <span style={{ fontSize: '0.5rem' }}>{getStatusIcon()}</span>
      <span style={{ fontSize: '0.4rem', fontWeight: 'bold' }}>WebSocket</span>
    </div>
  )
}

export default WebSocketStatus
