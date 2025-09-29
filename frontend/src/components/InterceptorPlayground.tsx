import React, { useRef } from 'react'
import { DetectorBadge } from './WebSocketStatus'

// Componente mínimo para probar el interceptor SIN tocar el resto de la app
// - No modifica charts ni hooks existentes
// - Solo registra un detector para Binance y loguea eventos

const InterceptorPlayground: React.FC = () => {
  const wsRef = useRef<WebSocket | null>(null)
  const cbWsRef = useRef<WebSocket | null>(null)
  // DetectorBadge maneja hook y estado internamente

  // useWsObserver ya maneja registro y limpieza

  // Mensajes/estado gestionados por el hook

  const connect = () => {
    if (wsRef.current) return
    const url = 'wss://stream.binance.com:9443/stream?streams=dogeusdt@kline_1m/dogeusdt@bookTicker'
    const ws = new WebSocket(url)
    wsRef.current = ws
  }

  const disconnect = () => {
    try {
      wsRef.current?.close(1000, 'manual close')
    } catch {}
    wsRef.current = null
  }

  const connectCoinbase = () => {
    if (cbWsRef.current) return
    const url = 'wss://ws-feed.exchange.coinbase.com'
    const ws = new WebSocket(url)
    cbWsRef.current = ws
    // Coinbase no emite datos hasta que recibe una suscripción
    ws.addEventListener('open', () => {
      const subscribe = {
        type: 'subscribe',
        product_ids: ['BTC-USD'],
        channels: ['ticker']
      }
      try {
        ws.send(JSON.stringify(subscribe))
      } catch {}
    })
    ws.addEventListener('close', () => {
      cbWsRef.current = null
    })
  }

  const disconnectCoinbase = () => {
    try {
      cbWsRef.current?.close(1000, 'manual close')
    } catch {}
    cbWsRef.current = null
  }

  return (
    <div style={{ padding: 16 }}>
      <h3>Interceptor Playground</h3>
      <p>Abre la consola. Verás logs cuando el WS de Binance conecte y reciba mensajes.</p>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        <button onClick={connect}>Conectar Binance</button>
        <button onClick={disconnect}>Desconectar Binance</button>
        <DetectorBadge
          label="Binance"
          id="pg-binance"
          urlContains={['binance', 'stream']}
          pulseThrottle={500}
        />
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button onClick={connectCoinbase}>Conectar Coinbase</button>
        <button onClick={disconnectCoinbase}>Desconectar Coinbase</button>
        <DetectorBadge
          label="Coinbase"
          id="pg-coinbase"
          urlContains={['coinbase', 'ws-feed']}
          pulseThrottle={500}
        />
      </div>
      <p>Este componente NO toca charts ni lógica de la app.</p>
    </div>
  )
}

export default InterceptorPlayground
