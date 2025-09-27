import { useEffect, useRef, useState } from 'react'
import { eventBus } from '../eventBus'

interface BinanceSocketOptions {
  symbol?: string // e.g. 'dogeusdt'
  interval?: string // e.g. '1m'
  enableKlines?: boolean
  enableBookTicker?: boolean
}

interface BinanceSocketState {
  isConnected: boolean
  isConnecting: boolean
  error: string | null
}

// Builds a Binance combined stream URL
function buildBinanceUrl(opts: Required<BinanceSocketOptions>): string {
  const streams: string[] = []
  if (opts.enableKlines) streams.push(`${opts.symbol}@kline_${opts.interval}`)
  if (opts.enableBookTicker) streams.push(`${opts.symbol}@bookTicker`)
  const streamPath = streams.join('/')
  return `wss://stream.binance.com:9443/stream?streams=${streamPath}`
}

export function useBinanceSocket(options: BinanceSocketOptions = {}): BinanceSocketState & {
  lastMessage: any
} {
  const opts: Required<BinanceSocketOptions> = {
    symbol: (options.symbol || 'dogeusdt').toLowerCase(),
    interval: options.interval || '1m',
    enableKlines: options.enableKlines !== false,
    enableBookTicker: options.enableBookTicker !== false
  }

  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastMessage, setLastMessage] = useState<any>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const url = buildBinanceUrl(opts)
    setIsConnecting(true)
    setError(null)

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      setIsConnecting(false)
      // Emit connection event to EventBus
      eventBus.emit('ws:binance:connected', { url, symbol: opts.symbol, interval: opts.interval })
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        // Normalize messages into { type, data }
        if (payload?.stream?.includes('@kline_')) {
          const msg = { type: 'binance.kline', data: payload.data }
          setLastMessage(msg)
          // Emit message event to EventBus
          eventBus.emit('ws:binance:message', {
            type: 'kline',
            data: payload.data,
            stream: payload.stream
          })
        } else if (payload?.stream?.endsWith('@bookTicker')) {
          const msg = { type: 'binance.bookTicker', data: payload.data }
          setLastMessage(msg)
          // Emit message event to EventBus
          eventBus.emit('ws:binance:message', {
            type: 'bookTicker',
            data: payload.data,
            stream: payload.stream
          })
        } else {
          const msg = { type: 'binance.raw', data: payload }
          setLastMessage(msg)
          // Emit message event to EventBus
          eventBus.emit('ws:binance:message', { type: 'raw', data: payload })
        }
      } catch (err) {
        // Ignore parse errors
      }
    }

    ws.onerror = () => {
      setError('WebSocket error')
      setIsConnecting(false)
      // Emit error event to EventBus
      eventBus.emit('ws:binance:error', { error: 'WebSocket error', url })
    }

    ws.onclose = () => {
      setIsConnected(false)
      setIsConnecting(false)
      // Emit disconnection event to EventBus
      eventBus.emit('ws:binance:disconnected', {
        url,
        symbol: opts.symbol,
        interval: opts.interval
      })
    }

    return () => {
      try {
        ws.close(1000, 'component unmount')
      } catch {}
      wsRef.current = null
    }
  }, [opts.symbol, opts.interval, opts.enableKlines, opts.enableBookTicker])

  return { isConnected, isConnecting, error, lastMessage }
}
