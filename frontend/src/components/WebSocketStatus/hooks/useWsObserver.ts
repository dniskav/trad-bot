import { useEffect, useMemo, useRef, useState } from 'react'
import { WSInterceptor } from '../utils/wsInterceptor'

export interface UseWsObserverOptions {
  id: string
  url?: string | string[]
  urlContains?: string | string[]
  pulseThrottle?: number
}

export interface UseWsObserverState {
  isConnected: boolean
  isConnecting: boolean
  pulsing: boolean
}

/**
 * React hook pequeño que registra un detector en WSInterceptor
 * y expone estado de conexión + pulso de mensajes.
 * No interfiere con instancias de WebSocket.
 */
export function useWsObserver(options: UseWsObserverOptions): UseWsObserverState {
  const { id, url, urlContains, pulseThrottle = 500 } = options
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [pulsing, setPulsing] = useState(false)
  const pulseTimeoutRef = useRef<number | null>(null)

  // Normalizar filtro para búsqueda en ventana (fallback)
  const filter = useMemo(() => ({ url, urlContains }), [url, urlContains])

  // Registrar detector
  useEffect(() => {
    WSInterceptor.addDetector({ id, url, urlContains, pulseThrottle })
    return () => WSInterceptor.removeDetector(id)
  }, [id, url, urlContains, pulseThrottle])

  // Suscribirse a eventos globales
  useEffect(() => {
    const match = (detail: any) => {
      const u: string = detail?.url || ''
      if (filter.url) {
        if (Array.isArray(filter.url)) {
          if (filter.url.includes(u)) return true
        } else if (u === filter.url) return true
      }
      if (filter.urlContains) {
        if (Array.isArray(filter.urlContains)) {
          if (filter.urlContains.some((k) => u.includes(k))) return true
        } else if (u.includes(filter.urlContains)) return true
      }
      return false
    }

    const onOpen = (e: any) => {
      if (match(e.detail)) {
        setIsConnected(true)
        setIsConnecting(false)
      }
    }
    const onClose = (e: any) => {
      if (match(e.detail)) {
        setIsConnected(false)
        setIsConnecting(false)
      }
    }
    const onMsg = (e: any) => {
      if (!match(e.detail)) return
      setPulsing(true)
      if (pulseTimeoutRef.current) clearTimeout(pulseTimeoutRef.current)
      pulseTimeoutRef.current = window.setTimeout(() => setPulsing(false), 400)
    }

    const onState = (e: any) => {
      if (!match(e.detail)) return
      const s = e.detail.state
      if (s) {
        setIsConnecting(!!s.isConnecting && !s.isConnected)
      }
    }

    window.addEventListener('ws:open', onOpen as any)
    window.addEventListener('ws:close', onClose as any)
    window.addEventListener('ws:message', onMsg as any)
    window.addEventListener('ws:state', onState as any)

    return () => {
      window.removeEventListener('ws:open', onOpen as any)
      window.removeEventListener('ws:close', onClose as any)
      window.removeEventListener('ws:message', onMsg as any)
      window.removeEventListener('ws:state', onState as any)
      if (pulseTimeoutRef.current) clearTimeout(pulseTimeoutRef.current)
    }
  }, [filter])

  return { isConnected, isConnecting, pulsing }
}

export default useWsObserver
