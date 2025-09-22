import React, { useContext, useEffect, useState } from 'react'
import { WebSocketContext } from '../contexts/WebSocketContext'
import { useSocket } from '../hooks/useSocket'

interface AppSetupProps {
  children: React.ReactNode
}

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  const [setupComplete, setSetupComplete] = useState(false)
  const [setupError, setSetupError] = useState<string | null>(null)

  // Contexto WebSocket
  const ctx = useContext(WebSocketContext)
  // console.log('🔌 AppSetup: ctx obtenido con useContext:', ctx) // Comentado para reducir spam

  // Hook useSocket para manejar la conexión WebSocket
  const socket = useSocket({
    url: 'ws://localhost:8000/ws?interval=1m',
    autoConnect: true, // Conectar automáticamente
    reconnectInterval: 3000,
    maxReconnectAttempts: 5,
    onMessage: (data) => {
      // console.log('📨 AppSetup: Mensaje recibido:', data)

      // Actualizar contexto con mensaje recibido
      if (ctx) {
        ctx.addMessage('received', data)
      }

      // También procesar los datos aquí para que estén disponibles globalmente
      // Esto es necesario porque AppContent no puede procesar los mensajes directamente
      // console.log('📨 AppSetup: Procesando mensaje para disponibilidad global:', data.type)
    },
    onOpen: () => {
      // console.log('✅ AppSetup: WebSocket conectado')

      // Actualizar contexto con estado de conexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: true, isConnecting: false, error: null })
      }
    },
    onClose: () => {
      // console.log('🔌 AppSetup: WebSocket desconectado')

      // Actualizar contexto con estado de desconexión
      if (ctx) {
        ctx.updateConnectionState({ isConnected: false, isConnecting: false })
      }
    },
    onError: (error) => {
      // console.error('❌ AppSetup: Error:', error)

      // Actualizar contexto con error
      if (ctx) {
        ctx.updateConnectionState({ error: `Error: ${error.type}`, isConnecting: false })
      }
    }
  })

  // Función para iniciar la conexión manualmente
  const handleConnect = () => {
    // console.log('🔄 AppSetup: Iniciando conexión manual...')
    socket.connect()
  }

  // Función para hacer las peticiones iniciales al servidor
  const performInitialSetup = async () => {
    try {
      // console.log('🚀 AppSetup: Iniciando configuración de la aplicación...')

      // Aquí puedes agregar todas las peticiones iniciales necesarias
      // Por ejemplo:
      // - Cargar configuración del usuario
      // - Verificar permisos
      // - Cargar datos iniciales
      // - etc.

      // console.log('✅ AppSetup: Configuración completada')
      setSetupComplete(true)
    } catch (err) {
      // console.error('❌ AppSetup: Error en configuración:', err)
      setSetupError('Error al configurar la aplicación')
    }
  }

  // Efecto para manejar el setup cuando el WebSocket esté listo
  useEffect(() => {
    if (socket.isConnected && !setupComplete && !setupError) {
      // console.log('🔌 AppSetup: WebSocket listo, iniciando setup...')
      performInitialSetup()
    }
  }, [socket.isConnected, setupComplete, setupError])

  // Resetear setup si el WebSocket se desconecta
  useEffect(() => {
    if (!socket.isConnected && setupComplete) {
      // console.log('🔄 AppSetup: WebSocket desconectado, reseteando setup...')
      setSetupComplete(false)
      setSetupError(null)
    }
  }, [socket.isConnected, setupComplete])

  // Mostrar loader mientras se configura
  if (!socket.isConnected || !setupComplete) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: '#1a1a1a',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          color: '#fbbf24'
        }}>
        {/* Icono animado */}
        <div
          style={{
            fontSize: '3rem',
            marginBottom: '1rem',
            animation: 'pulse 2s infinite'
          }}>
          🚀
        </div>

        {/* Título */}
        <div
          style={{
            fontSize: '1.5rem',
            fontWeight: 'bold',
            marginBottom: '0.5rem'
          }}>
          Trading Bot
        </div>

        {/* Estado del WebSocket */}
        <div
          style={{
            fontSize: '1rem',
            color: '#9ca3af',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
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
                : socket.error
                ? '#ef4444'
                : '#6b7280',
              animation: socket.isConnecting ? 'pulse 1s infinite' : 'none'
            }}
          />
          {socket.error && 'Error de conexión'}
          {!socket.error && socket.isConnecting && 'Conectando al servidor...'}
          {!socket.error && socket.isConnected && !setupComplete && 'Configurando aplicación...'}
          {!socket.error && !socket.isConnecting && !socket.isConnected && 'Offline'}
        </div>

        {/* Barra de progreso */}
        <div
          style={{
            width: '200px',
            height: '4px',
            backgroundColor: '#374151',
            borderRadius: '2px',
            overflow: 'hidden'
          }}>
          <div
            style={{
              width: socket.isConnected ? '100%' : socket.isConnecting ? '50%' : '0%',
              height: '100%',
              backgroundColor: socket.isConnected
                ? '#10b981'
                : socket.isConnecting
                ? '#fbbf24'
                : '#6b7280',
              borderRadius: '2px',
              transition: 'width 0.5s ease, background-color 0.5s ease'
            }}
          />
        </div>

        {/* Botón para conectar */}
        {!socket.isConnected && !socket.isConnecting && (
          <button
            onClick={handleConnect}
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '1rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'background-color 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = '#059669'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = '#10b981'
            }}>
            🔌 Conectar al Servidor
          </button>
        )}

        {/* Botón para desconectar */}
        {socket.isConnected && (
          <button
            onClick={() => socket.disconnect()}
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: '#ef4444',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '1rem',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'background-color 0.2s ease'
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.backgroundColor = '#dc2626'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.backgroundColor = '#ef4444'
            }}>
            🛑 Desconectar
          </button>
        )}

        {/* Mensaje de error */}
        {setupError && (
          <div
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#ef4444',
              color: 'white',
              borderRadius: '4px',
              fontSize: '0.9rem'
            }}>
            {setupError}
          </div>
        )}

        {/* Estilos CSS */}
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
      </div>
    )
  }

  // Mostrar la aplicación cuando todo esté listo
  return <>{children}</>
}

export default AppSetup
