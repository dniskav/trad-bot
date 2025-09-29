import { useCallback, useEffect, useRef, useState } from 'react'

export interface WebSocketDetectorState {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: number | null
}

export interface WebSocketDetectorOptions {
  url?: string | string[]
  urlContains?: string | string[]
  checkInterval?: number
  enablePulse?: boolean
  pulseThrottle?: number
  label?: string
}

/**
 * Hook simplificado para detectar WebSockets activos del browser
 * usando Network Information API y detección directa
 *
 * @param options - Configuración del detector
 * @param options.url - URL específica a detectar (opcional)
 * @param options.urlContains - Palabras que debe contener la URL (opcional)
 * @param options.checkInterval - Intervalo de verificación en ms (default: 3000)
 * @param options.enablePulse - Habilitar pulse visual (default: true)
 * @param options.pulseThrottle - Throttle del pulse en ms (default: 1000)
 * @param options.label - Label personalizado para el detector (default: 'WebSocket')
 */
export const useWebSocketDetector = (options: WebSocketDetectorOptions = {}) => {
  const {
    url,
    urlContains,
    checkInterval = 3000,
    enablePulse = true,
    pulseThrottle = 1000,
    label = 'WebSocket'
  } = options

  const [state, setState] = useState<WebSocketDetectorState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null
  })

  const intervalRef = useRef<number | null>(null)
  const lastPulseRef = useRef<number>(0)
  const originalWebSocketRef = useRef<typeof WebSocket | null>(null)

  // Función para verificar si una URL coincide con los criterios
  const matchesUrl = (
    wsUrl: string,
    config: { url?: string | string[]; urlContains?: string | string[] }
  ): boolean => {
    // Si no hay filtros definidos, no aceptar ninguna conexión
    if (!config.url && !config.urlContains) {
      return false
    }

    // Verificar URL exacta
    if (config.url) {
      if (Array.isArray(config.url)) {
        if (config.url.includes(wsUrl)) return true
      } else {
        if (wsUrl === config.url) return true
      }
    }

    // Verificar palabras clave en la URL
    if (config.urlContains) {
      if (Array.isArray(config.urlContains)) {
        // Solo coincidir si el array no está vacío
        if (config.urlContains.length > 0) {
          const matchedKeywords = config.urlContains.filter((keyword) => wsUrl.includes(keyword))
          if (matchedKeywords.length > 0) {
            return true
          }
        }
      } else {
        if (wsUrl.includes(config.urlContains)) return true
      }
    }

    return false
  }

  // Detectar conexiones WebSocket usando Network Information API
  const detectWebSocketConnections = useCallback(() => {
    // Deshabilitar detección automática para evitar falsos positivos
    // Solo confiar en el interceptor de WebSocket para detección real
    return
  }, [])

  // Monkey patch WebSocket para interceptar mensajes
  const setupWebSocketInterceptor = useCallback(() => {
    if (originalWebSocketRef.current) return // Ya está configurado

    // Capturar el WebSocket original ANTES de reemplazarlo
    const originalWebSocket = window.WebSocket
    originalWebSocketRef.current = originalWebSocket

    const InterceptedWebSocket = function (
      this: WebSocket,
      url: string,
      protocols?: string | string[]
    ) {
      // Usar la referencia capturada directamente para evitar recursión
      const ws = new (originalWebSocket as any)(url, protocols)

      // Verificar si la URL coincide con nuestros criterios
      const urlMatches = matchesUrl(ws.url, { url, urlContains })

      if (urlMatches) {
        // Monitorear estado de conexión usando readyState
        const monitorConnectionState = () => {
          const isConnected = ws.readyState === 1 // OPEN
          const isConnecting = ws.readyState === 0 // CONNECTING
          const hasError = ws.readyState === 3 // CLOSED

          setState((prev) => ({
            ...prev,
            isConnected,
            isConnecting,
            error: hasError ? 'Connection closed' : null
          }))
        }

        // Verificar estado inicial
        monitorConnectionState()

        // Monitorear cambios de estado periódicamente
        const stateInterval = setInterval(monitorConnectionState, 1000)

        // Limpiar intervalo cuando se cierre la conexión
        const originalClose = ws.close.bind(ws)
        ws.close = function (code?: number, reason?: string) {
          clearInterval(stateInterval)
          return originalClose(code, reason)
        }

        // Añadir un listener propio sin modificar la API del socket (no invasivo)
        if (enablePulse) {
          const pulseListener = (event: MessageEvent) => {
            const now = Date.now()
            const timeSinceLastPulse = now - lastPulseRef.current

            if (timeSinceLastPulse >= pulseThrottle) {
              setState((prev) => ({
                ...prev,
                lastMessage: now
              }))
              lastPulseRef.current = now
            }
          }

          ws.addEventListener('message', pulseListener)

          // Asegurar limpieza del listener al cerrar
          const removeOnClose = () => ws.removeEventListener('message', pulseListener)
          ws.addEventListener('close', removeOnClose, { once: true })
        }
      }

      return ws
    } as any

    // Copiar propiedades estáticas de forma segura
    try {
      Object.setPrototypeOf(InterceptedWebSocket, originalWebSocket)
      Object.defineProperty(InterceptedWebSocket, 'prototype', {
        value: originalWebSocket.prototype,
        writable: false
      })
    } catch (error) {
      // Si falla la copia de propiedades, continuar sin ellas
      console.warn('No se pudieron copiar las propiedades estáticas del WebSocket:', error)
    }

    // Reemplazar WebSocket global
    window.WebSocket = InterceptedWebSocket as any
  }, [url, urlContains, enablePulse, pulseThrottle])

  // Limpiar interceptor
  const cleanupWebSocketInterceptor = useCallback(() => {
    if (originalWebSocketRef.current) {
      window.WebSocket = originalWebSocketRef.current
      originalWebSocketRef.current = null
    }
  }, [])

  // Detectar conexiones periódicamente
  useEffect(() => {
    // Instalar interceptor de WebSocket una sola vez
    setupWebSocketInterceptor()

    // Detección inicial
    detectWebSocketConnections()

    // Detección periódica según configuración
    intervalRef.current = setInterval(detectWebSocketConnections, checkInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      // Limpiar interceptor al desmontar
      cleanupWebSocketInterceptor()
    }
  }, [checkInterval])

  // Detectar conexiones específicas basadas en configuración
  const detectTargetConnections = useCallback(() => {
    return {
      hasTargetConnection: false, // Siempre false para evitar falsos positivos
      targetConnections: []
    }
  }, [])

  return {
    ...state,
    label,
    detectTargetConnections,
    detectWebSocketConnections
  }
}

export default useWebSocketDetector
