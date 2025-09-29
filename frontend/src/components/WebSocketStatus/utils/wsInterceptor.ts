/*
 * Vanilla TypeScript WebSocket interceptor (singleton)
 * - Framework agnostic
 * - Non-invasive (does not override per-socket API; only adds listeners)
 * - Supports multiple detectors with strict URL matching
 */

export type DetectorId = string

export interface InterceptorState {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  lastMessage: number | null
}

export interface DetectorConfig {
  id: DetectorId
  url?: string | string[]
  urlContains?: string | string[]
  pulseThrottle?: number
  onState?: (state: InterceptorState) => void
  onMessage?: (event: MessageEvent) => void
}

export type GlobalEventType = 'ws:state' | 'ws:message' | 'ws:open' | 'ws:close' | 'ws:error'

export interface GlobalEventDetail {
  detectorId: DetectorId
  url: string
  state?: InterceptorState
  event?: MessageEvent
}

class WSInterceptorSingleton {
  private OriginalWS: typeof WebSocket | null = null
  private installed = false
  private detectors = new Map<DetectorId, DetectorConfig>()
  private observed = new WeakSet<WebSocket>()
  private lastPulseByDetector = new Map<DetectorId, number>()
  private bus: EventTarget = new EventTarget()

  private matchesUrl(url: string, cfg: Pick<DetectorConfig, 'url' | 'urlContains'>): boolean {
    if (!cfg.url && !cfg.urlContains) return false

    if (cfg.url) {
      if (Array.isArray(cfg.url)) {
        if (cfg.url.includes(url)) return true
      } else if (url === cfg.url) return true
    }

    if (cfg.urlContains) {
      if (Array.isArray(cfg.urlContains)) {
        if (cfg.urlContains.length && cfg.urlContains.some((k) => url.includes(k))) return true
      } else if (url.includes(cfg.urlContains)) return true
    }
    return false
  }

  private safeEmit<T>(fn: ((arg: T) => void) | undefined, arg: T): void {
    try {
      fn && fn(arg)
    } catch {
      /* no-op */
    }
  }

  private instrument(ws: WebSocket, url: string): void {
    if (this.observed.has(ws)) return
    this.observed.add(ws)

    for (const [id, cfg] of this.detectors) {
      if (!this.matchesUrl(url, cfg)) continue

      const emitState = () => {
        const state: InterceptorState = {
          isConnected: ws.readyState === WebSocket.OPEN,
          isConnecting: ws.readyState === WebSocket.CONNECTING,
          error: ws.readyState === WebSocket.CLOSED ? 'Connection closed' : null,
          lastMessage: null
        }
        this.safeEmit(cfg.onState, state)
        this.dispatch('ws:state', { detectorId: id, url, state })
      }

      emitState()
      const interval = setInterval(emitState, 1000)

      const pulseListener = (event: MessageEvent) => {
        const now = Date.now()
        const last = this.lastPulseByDetector.get(id) || 0
        const throttle = cfg.pulseThrottle ?? 1000
        if (now - last >= throttle) {
          this.safeEmit(cfg.onState, {
            isConnected: ws.readyState === WebSocket.OPEN,
            isConnecting: ws.readyState === WebSocket.CONNECTING,
            error: null,
            lastMessage: now
          })
          this.lastPulseByDetector.set(id, now)
        }
        this.safeEmit(cfg.onMessage, event)
        this.dispatch('ws:message', { detectorId: id, url, event })
      }

      ws.addEventListener('message', pulseListener)
      const cleanup = () => {
        clearInterval(interval)
        ws.removeEventListener('message', pulseListener)
      }
      ws.addEventListener(
        'close',
        () => {
          cleanup()
          this.dispatch('ws:close', { detectorId: id, url })
        },
        { once: true }
      )
      ws.addEventListener('open', () => this.dispatch('ws:open', { detectorId: id, url }))
      ws.addEventListener('error', () => {
        const state: InterceptorState = {
          isConnected: ws.readyState === WebSocket.OPEN,
          isConnecting: ws.readyState === WebSocket.CONNECTING,
          error: 'WebSocket error',
          lastMessage: null
        }
        this.safeEmit(cfg.onState, state)
        this.dispatch('ws:error', { detectorId: id, url, state })
      })
    }
  }

  start(): void {
    if (this.installed) return
    if (!this.OriginalWS) this.OriginalWS = window.WebSocket
    const OriginalWS = this.OriginalWS
    const self = this

    // Use a constructible function (not arrow) to support `new WebSocket(...)`
    function InterceptedWebSocket(this: any, url: string | URL, protocols?: string | string[]) {
      const ws = new (OriginalWS as any)(url, protocols)
      try {
        self.instrument(ws, (ws as any).url as string)
      } catch {
        /* no-op */
      }
      return ws as any
    }

    Object.setPrototypeOf(InterceptedWebSocket, OriginalWS)
    Object.defineProperty(InterceptedWebSocket, 'prototype', {
      value: (OriginalWS as any).prototype
    })
    window.WebSocket = InterceptedWebSocket as any
    this.installed = true
  }

  stop(): void {
    if (!this.installed || !this.OriginalWS) return
    window.WebSocket = this.OriginalWS
    this.installed = false
  }

  addDetector(cfg: DetectorConfig): void {
    this.detectors.set(cfg.id, cfg)
    this.start()
  }

  removeDetector(id: DetectorId): void {
    this.detectors.delete(id)
    if (this.detectors.size === 0) this.stop()
  }

  isInstalled(): boolean {
    return this.installed
  }

  on(type: GlobalEventType, listener: (ev: CustomEvent<GlobalEventDetail>) => void): void {
    this.bus.addEventListener(type, listener as EventListener)
  }

  off(type: GlobalEventType, listener: (ev: CustomEvent<GlobalEventDetail>) => void): void {
    this.bus.removeEventListener(type, listener as EventListener)
  }

  private dispatch(type: GlobalEventType, detail: GlobalEventDetail): void {
    const ev = new CustomEvent(type, { detail })
    this.bus.dispatchEvent(ev)
    // También emitir a window para permitir window.addEventListener('ws:*', ...)
    try {
      window.dispatchEvent(ev)
    } catch {
      // noop
    }
  }
}

export const WSInterceptor = new WSInterceptorSingleton()

// Opcional: exponer para debug desde DevTools sin depender del bundler
// No afecta funcionalidad en producción
;(window as any).__WSInterceptor__ = WSInterceptor
