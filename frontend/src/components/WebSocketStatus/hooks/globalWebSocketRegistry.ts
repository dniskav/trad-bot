/**
 * Registro global para manejar múltiples detectores WebSocket
 * Permite que varios componentes compartan un solo interceptor de WebSocket
 */

export interface WebSocketDetectorConfig {
  id: string
  url?: string | string[]
  urlContains?: string | string[]
  enablePulse?: boolean
  pulseThrottle?: number
  label?: string
  onStateChange?: (state: WebSocketDetectorState) => void
  onMessage?: (message: any) => void
}

export interface WebSocketDetectorState {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: number | null
}

class GlobalWebSocketRegistry {
  private originalWebSocket: typeof WebSocket | null = null
  private isInterceptorActive = false
  private detectors = new Map<string, WebSocketDetectorConfig>()
  private lastPulseTimes = new Map<string, number>()

  /**
   * Registrar un nuevo detector
   */
  registerDetector(config: WebSocketDetectorConfig): void {
    this.detectors.set(config.id, config)
    this.setupInterceptor()
  }

  /**
   * Desregistrar un detector
   */
  unregisterDetector(id: string): void {
    this.detectors.delete(id)
    this.lastPulseTimes.delete(id)

    // Si no hay más detectores, limpiar el interceptor
    if (this.detectors.size === 0) {
      this.cleanupInterceptor()
    }
  }

  /**
   * Configurar el interceptor de WebSocket (solo una vez)
   */
  private setupInterceptor(): void {
    if (this.isInterceptorActive || this.originalWebSocket) {
      return // Ya está configurado
    }

    this.originalWebSocket = window.WebSocket
    this.isInterceptorActive = true

    // Capturar referencias para usar dentro de la función
    const originalWebSocket = this.originalWebSocket
    const registry = this

    const InterceptedWebSocket = function (
      this: WebSocket,
      url: string,
      protocols?: string | string[]
    ) {
      // Crear WebSocket real usando la referencia original directamente para evitar recursión
      const ws = new (originalWebSocket as any)(url, protocols)

      // Notificar a todos los detectores relevantes
      registry.notifyDetectors(ws, url)

      return ws
    }

    // Copiar propiedades estáticas
    Object.setPrototypeOf(InterceptedWebSocket, originalWebSocket)
    Object.defineProperty(InterceptedWebSocket, 'prototype', {
      value: originalWebSocket.prototype,
      writable: false
    })

    // Reemplazar WebSocket global
    window.WebSocket = InterceptedWebSocket as any
  }

  /**
   * Notificar a los detectores relevantes sobre una nueva conexión WebSocket
   */
  private notifyDetectors(ws: WebSocket, url: string): void {
    for (const [detectorId, config] of this.detectors) {
      // Verificar si esta conexión coincide con los criterios del detector
      const urlMatches = this.matchesUrl(url, config)

      if (urlMatches) {
        // Monitorear estado de conexión
        this.monitorConnection(ws, detectorId, config)

        // Interceptar mensajes si está habilitado el pulse
        if (config.enablePulse) {
          this.interceptMessages(ws, detectorId, config)
        }
      }
    }
  }

  /**
   * Verificar si una URL coincide con los criterios de un detector
   */
  private matchesUrl(url: string, config: WebSocketDetectorConfig): boolean {
    // Si no hay filtros definidos, no aceptar ninguna conexión
    if (!config.url && !config.urlContains) {
      return false
    }

    // Verificar URL exacta
    if (config.url) {
      if (Array.isArray(config.url)) {
        if (config.url.includes(url)) return true
      } else {
        if (url === config.url) return true
      }
    }

    // Verificar palabras clave en la URL
    if (config.urlContains) {
      if (Array.isArray(config.urlContains)) {
        // Solo coincidir si el array no está vacío
        if (config.urlContains.length > 0) {
          const matchedKeywords = config.urlContains.filter((keyword) => url.includes(keyword))
          if (matchedKeywords.length > 0) {
            return true
          }
        }
      } else {
        if (url.includes(config.urlContains)) return true
      }
    }

    return false
  }

  /**
   * Monitorear el estado de una conexión WebSocket
   */
  private monitorConnection(
    ws: WebSocket,
    _detectorId: string,
    config: WebSocketDetectorConfig
  ): void {
    const updateState = () => {
      const isConnected = ws.readyState === 1 // OPEN
      const isConnecting = ws.readyState === 0 // CONNECTING
      const hasError = ws.readyState === 3 // CLOSED

      const state: WebSocketDetectorState = {
        isConnected,
        isConnecting,
        error: hasError ? 'Connection closed' : null,
        lastMessage: null
      }

      config.onStateChange?.(state)
    }

    // Estado inicial
    updateState()

    // Monitorear cambios de estado
    const stateInterval = setInterval(updateState, 1000)

    // Limpiar cuando se cierre la conexión
    const originalClose = ws.close.bind(ws)
    ws.close = function (code?: number, reason?: string) {
      clearInterval(stateInterval)
      return originalClose(code, reason)
    }
  }

  /**
   * Interceptar mensajes para el pulse
   */
  private interceptMessages(
    ws: WebSocket,
    detectorId: string,
    config: WebSocketDetectorConfig
  ): void {
    const originalAddEventListener = ws.addEventListener.bind(ws)
    const registry = this

    ws.addEventListener = function (
      type: string,
      listener: EventListenerOrEventListenerObject,
      options?: boolean | AddEventListenerOptions
    ) {
      if (type === 'message') {
        const wrappedListener = (event: MessageEvent) => {
          const now = Date.now()
          const lastPulse = registry.lastPulseTimes.get(detectorId) || 0
          const timeSinceLastPulse = now - lastPulse

          // Throttle del pulse
          if (timeSinceLastPulse >= (config.pulseThrottle || 1000)) {
            // Actualizar estado inmediatamente para el pulse
            const state: WebSocketDetectorState = {
              isConnected: ws.readyState === 1,
              isConnecting: ws.readyState === 0,
              error: null,
              lastMessage: now
            }
            config.onStateChange?.(state)

            registry.lastPulseTimes.set(detectorId, now)
          }

          // Llamar al listener original
          if (typeof listener === 'function') {
            listener(event)
          } else if (listener && typeof listener === 'object' && 'handleEvent' in listener) {
            listener.handleEvent(event)
          }
        }

        return originalAddEventListener(type, wrappedListener, options)
      }

      return originalAddEventListener(type, listener, options)
    }
  }

  /**
   * Limpiar el interceptor
   */
  private cleanupInterceptor(): void {
    if (this.originalWebSocket && this.isInterceptorActive) {
      window.WebSocket = this.originalWebSocket
      this.originalWebSocket = null
      this.isInterceptorActive = false
    }
  }

  /**
   * Obtener información de todos los detectores registrados
   */
  getDetectorsInfo(): Array<{ id: string; config: WebSocketDetectorConfig }> {
    return Array.from(this.detectors.entries()).map(([id, config]) => ({ id, config }))
  }
}

// Instancia global única
export const globalWebSocketRegistry = new GlobalWebSocketRegistry()
