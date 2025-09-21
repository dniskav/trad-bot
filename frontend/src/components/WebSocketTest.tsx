import React, { useContext, useState } from 'react'
import { WebSocketContext } from '../contexts/WebSocketContext'
import { useSocket } from '../hooks/useSocket'

const WebSocketTest: React.FC = () => {
  console.log('🧪 WebSocketTest: Componente montado')

  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState<string[]>([])

  // Usar useContext directamente
  const ctx = useContext(WebSocketContext)

  const socket = useSocket({
    url: 'ws://localhost:8000/ws?interval=1m',
    autoConnect: false, // Deshabilitado para evitar bucles
    reconnectInterval: 3000,
    maxReconnectAttempts: 3,
    onMessage: (data) => {
      console.log('📨 WebSocketTest: Mensaje recibido:', data)
      setMessages((prev) => [...prev, `Recibido: ${JSON.stringify(data)}`])
      // Actualizar contexto con mensaje recibido
      if (ctx) {
        ctx.addMessage('received', data)
      }
    },
    onOpen: () => {
      console.log('✅ WebSocketTest: WebSocket conectado')
      setMessages((prev) => [...prev, '✅ Conectado'])
      // Actualizar contexto con estado de conexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: true, isConnecting: false, error: null })
      }
    },
    onClose: () => {
      console.log('🔌 WebSocketTest: WebSocket desconectado')
      setMessages((prev) => [...prev, '🔌 Desconectado'])
      // Actualizar contexto con estado de desconexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: false, isConnecting: false })
      }
    },
    onError: (error) => {
      console.error('❌ WebSocketTest: Error:', error)
      setMessages((prev) => [...prev, `❌ Error: ${error.type}`])
      // Actualizar contexto con error
      if (ctx) {
        ctx.updateConnectionState({ error: `Error: ${error.type}`, isConnecting: false })
      }
    }
  })

  const handleSendMessage = () => {
    if (message.trim()) {
      socket.send(message)
      setMessages((prev) => [...prev, `Enviado: ${message}`])
      // Actualizar contexto con mensaje enviado
      if (ctx) {
        ctx.addMessage('sent', message)
      }
      setMessage('')
    }
  }

  const handleConnect = () => {
    socket.connect()
    setMessages((prev) => [...prev, '🔄 Intentando conectar...'])
    // Actualizar contexto con estado de conexión
    if (ctx) {
      ctx.updateConnectionState({ isConnecting: true, error: null })
    }
  }

  const handleDisconnect = () => {
    socket.disconnect()
    setMessages((prev) => [...prev, '🛑 Desconectando...'])
    // Actualizar contexto con estado de desconexión
    if (ctx) {
      ctx.updateConnectionState({ isConnected: false, isConnecting: false })
    }
  }

  const clearMessages = () => {
    setMessages([])
    // Limpiar mensajes del contexto también
    if (ctx) {
      ctx.clearMessages()
    }
  }

  return (
    <div
      style={{
        padding: '20px',
        backgroundColor: '#1a1a1a',
        color: 'white',
        borderRadius: '8px',
        margin: '20px',
        fontFamily: 'monospace'
      }}>
      <h2 style={{ color: '#fbbf24', marginBottom: '20px' }}>🧪 WebSocket Test Component</h2>

      {/* Toggle para usar contexto */}
      <div style={{ marginBottom: '20px' }}>
        {ctx && (
          <div style={{ color: '#10b981', fontSize: '0.9rem', marginTop: '5px' }}>
            ✅ Contexto WebSocket disponible
          </div>
        )}
        {!ctx && (
          <div style={{ color: '#f59e0b', fontSize: '0.9rem', marginTop: '5px' }}>
            ⚠️ No hay contexto WebSocket disponible
          </div>
        )}
      </div>

      {/* Estado del WebSocket */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Estado del WebSocket:</h3>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span
            style={{
              display: 'inline-block',
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: socket.isConnecting
                ? '#f59e0b'
                : socket.isConnected
                ? '#10b981'
                : '#ef4444'
            }}
          />
          <span>
            {socket.isConnecting && '🟡 Conectando...'}
            {socket.isConnected && '🟢 Conectado'}
            {!socket.isConnecting && !socket.isConnected && '🔴 Desconectado'}
          </span>
          {socket.error && <span style={{ color: '#ef4444' }}>Error: {socket.error}</span>}
          {socket.reconnectAttempts > 0 && (
            <span style={{ color: '#f59e0b' }}>Intentos: {socket.reconnectAttempts}</span>
          )}
        </div>
      </div>

      {/* Controles */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Controles:</h3>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          <button
            onClick={handleConnect}
            disabled={socket.isConnecting || socket.isConnected}
            style={{
              padding: '8px 16px',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: socket.isConnecting || socket.isConnected ? 'not-allowed' : 'pointer',
              opacity: socket.isConnecting || socket.isConnected ? 0.5 : 1
            }}>
            Conectar
          </button>
          <button
            onClick={handleDisconnect}
            disabled={!socket.isConnected}
            style={{
              padding: '8px 16px',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: !socket.isConnected ? 'not-allowed' : 'pointer',
              opacity: !socket.isConnected ? 0.5 : 1
            }}>
            Desconectar
          </button>
          <button
            onClick={clearMessages}
            style={{
              padding: '8px 16px',
              backgroundColor: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}>
            Limpiar
          </button>
        </div>
      </div>

      {/* Enviar mensaje */}
      <div style={{ marginBottom: '20px' }}>
        <h3>Enviar mensaje:</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Escribe un mensaje..."
            style={{
              flex: 1,
              padding: '8px',
              backgroundColor: '#374151',
              color: 'white',
              border: '1px solid #6b7280',
              borderRadius: '4px'
            }}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          />
          <button
            onClick={handleSendMessage}
            disabled={!socket.isConnected || !message.trim()}
            style={{
              padding: '8px 16px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: !socket.isConnected || !message.trim() ? 'not-allowed' : 'pointer',
              opacity: !socket.isConnected || !message.trim() ? 0.5 : 1
            }}>
            Enviar
          </button>
        </div>
      </div>

      {/* Último mensaje del hook */}
      {socket.lastMessage && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Último mensaje del hook:</h3>
          <pre
            style={{
              backgroundColor: '#374151',
              padding: '10px',
              borderRadius: '4px',
              overflow: 'auto',
              maxHeight: '200px'
            }}>
            {JSON.stringify(socket.lastMessage, null, 2)}
          </pre>
        </div>
      )}

      {/* Mensajes del contexto */}
      {ctx && (
        <div style={{ marginBottom: '20px' }}>
          <h3>Mensajes del contexto ({ctx.messages.length}):</h3>
          <div
            style={{
              backgroundColor: '#374151',
              padding: '10px',
              borderRadius: '4px',
              maxHeight: '200px',
              overflow: 'auto'
            }}>
            {ctx.messages.length === 0 ? (
              <div style={{ color: '#9ca3af' }}>No hay mensajes en el contexto...</div>
            ) : (
              ctx.messages.map((msg) => (
                <div key={msg.id} style={{ marginBottom: '5px', fontSize: '0.9rem' }}>
                  <span style={{ color: msg.type === 'sent' ? '#10b981' : '#3b82f6' }}>
                    {msg.type === 'sent' ? '📤' : '📨'}
                  </span>
                  <span style={{ color: '#9ca3af', marginLeft: '5px' }}>
                    {new Date(msg.timestamp).toLocaleTimeString()}:
                  </span>
                  <span style={{ marginLeft: '5px' }}>
                    {typeof msg.message === 'string' ? msg.message : JSON.stringify(msg.message)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Historial de mensajes */}
      <div>
        <h3>Historial de mensajes:</h3>
        <div
          style={{
            backgroundColor: '#374151',
            padding: '10px',
            borderRadius: '4px',
            maxHeight: '300px',
            overflow: 'auto'
          }}>
          {messages.length === 0 ? (
            <div style={{ color: '#9ca3af' }}>No hay mensajes aún...</div>
          ) : (
            messages.map((msg, index) => (
              <div key={index} style={{ marginBottom: '5px' }}>
                {msg}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default WebSocketTest
