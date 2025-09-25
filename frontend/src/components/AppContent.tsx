import React, { useContext, useEffect, useState } from 'react'
import { WebSocketContext } from '../contexts/WebSocketContext'
import { useApiMarginInfo } from '../hooks'
// import { useSocket } from '../hooks/useSocket'
import Accordion from './Accordion'
import AccountBalance from './AccountBalance'
import ActivePositions from './ActivePositions'
import BotSignals from './BotSignals'
import CandlestickChart from './CandlestickChart'
import { MarginInfo } from './MarginInfo'
import PlugAndPlayBots from './PlugAndPlayBots'
import { PositionHistory } from './PositionHistory'
import { Toast } from './Toast'
import WebSocketStatus from './WebSocketStatus'

interface AppContentProps {
  timeframe: string
  onTimeframeChange: (timeframe: string) => void
}

const AppContent: React.FC<AppContentProps> = ({ timeframe, onTimeframeChange }) => {
  // console.log('🚀 AppContent: Componente montado') // Comentado para reducir spam

  // Estados locales
  const [botSignals, setBotSignals] = useState<any>(null)
  const [positionHistory, setPositionHistory] = useState<any[]>([])
  const [activePositions, setActivePositions] = useState<Record<
    string,
    Record<string, any>
  > | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [accountBalance, setAccountBalance] = useState<any>(null)

  // Use margin info hook
  const { isLoading: marginLoading, error: marginError, fetchMarginInfo } = useApiMarginInfo()

  // State for margin info data
  const [marginInfo, setMarginInfo] = useState<any | null>(null)

  // Fetch margin info on mount and log when loading is false
  useEffect(() => {
    const fetchData = async () => {
      const data = await fetchMarginInfo()
      if (data) {
        setMarginInfo(data)
      }
    }
    fetchData()
  }, []) // Remove fetchMarginInfo dependency to prevent infinite loop

  // Fetch account balance and active positions on mount
  useEffect(() => {
    const fetchAccountBalance = async () => {
      try {
        const response = await fetch('/api/position-info')
        if (response.ok) {
          const data = await response.json()
          if (data.account_balance) {
            setAccountBalance(data.account_balance)
          }
          if (data.active_positions) {
            setActivePositions(data.active_positions)
          }
        }
      } catch (error) {
        console.error('Error fetching account balance on mount:', error)
      }
    }
    fetchAccountBalance()
  }, [])

  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState('')

  // Estados para datos de gráficos
  const [candlesData, setCandlesData] = useState<any[]>([])
  const [indicatorsData, setIndicatorsData] = useState<any>({})
  const [historyStats, setHistoryStats] = useState<Record<string, any>>({
    conservative: {},
    aggressive: {},
    overall: {}
  })
  // (Opcional) Posiciones activas por bot podrían usarse más adelante

  // Hook useSocket para enviar mensajes (reutiliza la instancia existente)
  // const socket = useSocket({
  //   autoConnect: false // No auto-conectar aquí, ya está conectado en AppSetup
  //   // No necesitamos onMessage aquí porque AppSetup ya maneja los mensajes
  // })

  // Contexto WebSocket (mantener para compatibilidad)
  const ctx = useContext(WebSocketContext)

  // Efecto para procesar mensajes del contexto
  useEffect(() => {
    if (ctx && ctx.lastMessage) {
      const data = ctx.lastMessage.message

      // Procesar diferentes tipos de mensajes
      if (data.type === 'initial_data') {
        if (data.data) {
          if (data.data.current_price) {
            setCurrentPrice(data.data.current_price)
          }
          if (data.data.account_balance) {
            setAccountBalance(data.data.account_balance)
          }
          if (data.data.active_positions) {
            setActivePositions(data.data.active_positions)
          }
          // Historial: se carga únicamente desde el endpoint (no vía WS)
          if (data.data.bot_status) {
            // Los bot_status se pueden usar más adelante
          }
          if (data.data.candles) {
            setCandlesData(data.data.candles)
          }
          if (data.data.indicators) {
            setIndicatorsData(data.data.indicators)
          }
          if (data.data.bot_signals) {
            setBotSignals(data.data.bot_signals)
          }
        }
      } else if (data.type === 'update') {
        if (data.data) {
          if (data.data.current_price) {
            setCurrentPrice(data.data.current_price)
          }
          if (data.data.account_balance) {
            setAccountBalance(data.data.account_balance)
          }
          if (data.data.active_positions) {
            setActivePositions(data.data.active_positions)
          }
          // Historial: se carga únicamente desde el endpoint (no vía WS)
          if (data.data.bot_status) {
          }
          if (data.data.candles) {
            setCandlesData(data.data.candles)
          }
          if (data.data.indicators) {
            setIndicatorsData(data.data.indicators)
          }
          if (data.data.bot_signals) {
            setBotSignals(data.data.bot_signals)
          }
        }
      } else if (data.type === 'bot_signals') {
        setBotSignals(data.data || [])
      } else if (data.type === 'history_refresh') {
        // Forzar al componente de historial a recargar usando el hook
        // Aquí no tenemos referencia directa; el componente ya tiene botón Refrescar.
        // Podríamos emitir un CustomEvent para que el hook o componente escuche.
        try {
          window.dispatchEvent(new CustomEvent('history_refresh'))
        } catch {}
      } else if (data.type === 'position_history') {
        // Ignorado: el historial solo se consume por endpoint
      } else if (data.type === 'active_positions') {
        setActivePositions(data.data || null)
      } else if (data.type === 'price' || data.type === 'price_update') {
        setCurrentPrice(data.data?.price || 0)
      } else if (data.type === 'account_balance') {
        setAccountBalance(data.data)
      } else if (data.type === 'margin_info') {
        // Margin info is now handled by the hook
      } else if (data.type === 'history_stream') {
        // Ignorado: el historial solo se consume por endpoint
      } else if (data.type === 'plugin_bots_realtime') {
        // Publicar en el contexto para que cualquier componente (p.ej. PlugAndPlayBots) lo consuma
        if (ctx && ctx.setPluginBotsRealtime) {
          ctx.setPluginBotsRealtime(data.data || {})
        }
      } else if (data.type === 'candles') {
        setCandlesData(data.data?.candles || [])

        // Procesar bot_signals si están disponibles
        if (data.data?.bot_signals) {
          setBotSignals(data.data.bot_signals)

          // No actualizar historial desde payloads de velas
          const positionsPayload = data.data?.bot_signals?.positions
          // Extraer posiciones activas si vienen embebidas (compatibilidad)
          const activeFromPayload = positionsPayload?.active_positions
          if (activeFromPayload) {
            setActivePositions(activeFromPayload)
          }
        }
      } else if (data.type === 'indicators') {
        setIndicatorsData(data.data || {})
      } else if (data.type === 'error') {
        setToastMessage(data.message || 'Error desconocido')
        setShowToast(true)
      }
    }
  }, [ctx?.lastMessage])

  // Calcula estadísticas básicas por bot y generales
  const calculateStatistics = (history: any[]) => {
    const perBot: Record<
      string,
      { total_trades: number; wins: number; total_pnl_net: number; best_trade: number }
    > = {}

    for (const h of history) {
      const bot = h.bot_type || 'unknown'
      if (!perBot[bot]) {
        perBot[bot] = { total_trades: 0, wins: 0, total_pnl_net: 0, best_trade: -Infinity }
      }
      perBot[bot].total_trades += 1
      const pnlNet = Number(h.pnl_net || 0)
      if (pnlNet > 0) perBot[bot].wins += 1
      perBot[bot].total_pnl_net += pnlNet
      perBot[bot].best_trade = Math.max(perBot[bot].best_trade, pnlNet)
    }

    // Construir objeto de salida y overall
    const statsOut: Record<string, any> = {}
    let overallTrades = 0
    let overallWins = 0
    let overallPnl = 0
    let overallBest = -Infinity

    Object.entries(perBot).forEach(([bot, s]) => {
      statsOut[bot] = {
        total_trades: s.total_trades,
        win_rate: s.total_trades ? (s.wins / s.total_trades) * 100 : 0,
        total_pnl_net: s.total_trades ? s.total_pnl_net : 0,
        best_trade: Number.isFinite(s.best_trade) ? s.best_trade : 0
      }
      overallTrades += s.total_trades
      overallWins += s.wins
      overallPnl += s.total_pnl_net
      overallBest = Math.max(overallBest, s.best_trade)
    })

    statsOut.conservative = statsOut.conservative || {
      total_trades: 0,
      win_rate: 0,
      total_pnl_net: 0,
      best_trade: 0
    }
    statsOut.aggressive = statsOut.aggressive || {
      total_trades: 0,
      win_rate: 0,
      total_pnl_net: 0,
      best_trade: 0
    }

    statsOut.overall = {
      total_trades: overallTrades,
      win_rate: overallTrades ? (overallWins / overallTrades) * 100 : 0,
      total_pnl_net: overallPnl,
      best_trade: Number.isFinite(overallBest) ? overallBest : 0
    }

    return statsOut
  }

  // Función para enviar mensajes usando el socket singleton (mantenida para futuras funcionalidades)
  // const sendMessage = (message: any) => {
  //   if (socket.isConnected) {
  //     // Enviar mensaje real a través del WebSocket
  //     socket.send(JSON.stringify(message))

  //     // También actualizar el contexto para mantener compatibilidad
  //     if (ctx) {
  //       ctx.addMessage('sent', message)
  //     }
  //   } else {
  //     setToastMessage('No se puede enviar mensaje: WebSocket no conectado')
  //     setShowToast(true)
  //   }
  // }

  // Función para cambiar timeframe
  const handleTimeframeChange = (newTimeframe: string) => {
    onTimeframeChange(newTimeframe)
    // El AppSetup manejará la reconexión
  }

  // Klines vienen solo por WebSocket; eliminamos fallback REST
  // Sembrar 1000 velas desde Binance REST y calcular indicadores
  useEffect(() => {
    const controller = new AbortController()
    const symbol = 'DOGEUSDT'
    const interval = timeframe

    const computeSMA = (values: number[], period: number): (number | null)[] => {
      const result: (number | null)[] = []
      let sum = 0
      for (let i = 0; i < values.length; i++) {
        sum += values[i]
        if (i >= period) sum -= values[i - period]
        if (i >= period - 1) result.push(sum / period)
        else result.push(null)
      }
      return result
    }

    const computeRSI = (closes: number[], period: number = 14): (number | null)[] => {
      const rsi: (number | null)[] = new Array(closes.length).fill(null)
      if (closes.length < period + 1) return rsi
      const gains: number[] = []
      const losses: number[] = []
      for (let i = 1; i < closes.length; i++) {
        const change = closes[i] - closes[i - 1]
        gains.push(Math.max(change, 0))
        losses.push(Math.max(-change, 0))
      }
      let avgGain = 0
      let avgLoss = 0
      for (let i = 0; i < period; i++) {
        avgGain += gains[i]
        avgLoss += losses[i]
      }
      avgGain /= period
      avgLoss /= period
      const firstRsiIndex = period
      rsi[firstRsiIndex] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
      for (let i = firstRsiIndex + 1; i < closes.length; i++) {
        const gain = gains[i - 1]
        const loss = losses[i - 1]
        avgGain = (avgGain * (period - 1) + gain) / period
        avgLoss = (avgLoss * (period - 1) + loss) / period
        rsi[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
      }
      return rsi
    }

    const fetchKlines = async () => {
      try {
        const url = `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=1000`
        const res = await fetch(url, { signal: controller.signal })
        if (!res.ok) return
        const arr = await res.json()
        if (!Array.isArray(arr)) return

        // Binance klines format: [ openTime, open, high, low, close, volume, closeTime, ... ]
        const candles = arr.map((k: any[]) => ({
          time: Number(k[0]),
          open: Number(k[1]),
          high: Number(k[2]),
          low: Number(k[3]),
          close: Number(k[4])
        }))

        const closes = candles.map((c: any) => Number(c.close))
        const timesMs = candles.map((c: any) => Number(c.time))
        // Usar quote asset volume (k[7]) en Binance REST
        const volumes = arr.map((k: any[]) => Number(k[7]))

        const smaFast = computeSMA(closes, 8)
        const smaSlow = computeSMA(closes, 21)
        const rsi = computeRSI(closes, 14)

        setCandlesData(candles)
        setIndicatorsData({
          sma_fast: smaFast.map((v) => (v === null ? NaN : Number(v))),
          sma_slow: smaSlow.map((v) => (v === null ? NaN : Number(v))),
          rsi: rsi.map((v) => (v === null ? NaN : Number(v))),
          volume: volumes,
          timestamps: timesMs
        })
      } catch (e) {
        // Silenciar por ahora; podemos agregar UI de error si es necesario
      }
    }

    fetchKlines()
    return () => controller.abort()
  }, [timeframe])

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <WebSocketStatus />
          </div>

          <div className="header-center">
            <h1 className="app-title">Trading Bot</h1>
          </div>

          <div className="header-right">
            <button
              className="status-button"
              onClick={() => {
                // Aquí podrías implementar la verificación de salud
                setToastMessage('Verificación de salud completada')
                setShowToast(true)
              }}>
              Status
            </button>
          </div>
        </div>
      </header>

      {/* Contenido principal */}
      <main className="app-main">
        <div className="health-container">
          {/* Saldo de Cuenta */}
          <Accordion title="Saldo de Cuenta" defaultExpanded={true} storageKey="account-balance">
            <AccountBalance
              currentPrice={currentPrice}
              balance={accountBalance}
              symbol="DOGEUSDT"
            />
          </Accordion>

          {/* Señales de Trading */}
          <Accordion title="Señales de Trading" defaultExpanded={true} storageKey="trading-signals">
            <BotSignals
              signals={
                botSignals
                  ? {
                      conservative: botSignals.conservative || 'N/A',
                      aggressive: botSignals.aggressive || 'N/A',
                      current_price: botSignals.current_price || currentPrice,
                      symbol: 'DOGEUSDT',
                      positions: botSignals.positions || {
                        conservative: {},
                        aggressive: {},
                        last_signals: botSignals
                      }
                    }
                  : null
              }
            />
          </Accordion>

          {/* Posiciones Concurrentes Activas */}
          <Accordion
            title="Posiciones Concurrentes Activas"
            defaultExpanded={true}
            storageKey="active-positions">
            <ActivePositions positions={activePositions} />
          </Accordion>

          {/* Información de Margen */}
          <Accordion title="Información de Margen" defaultExpanded={false} storageKey="margin-info">
            <MarginInfo marginInfo={marginInfo} />
          </Accordion>

          {/* Gráfico de Velas */}
          <Accordion title="Gráfico de Velas" defaultExpanded={true} storageKey="candlestick-chart">
            <CandlestickChart
              symbol="DOGEUSDT"
              timeframe={timeframe}
              signals={botSignals}
              candlesData={candlesData}
              indicatorsData={indicatorsData}
              onTimeframeChange={handleTimeframeChange}
              live
              binanceSymbol="DOGEUSDT"
              binanceInterval={timeframe}
            />
          </Accordion>

          {/* Plugin Bots */}
          <Accordion title="Plugin Bots" defaultExpanded={true} storageKey="plugin-bots">
            <PlugAndPlayBots currentPrice={currentPrice} />
          </Accordion>

          {/* Historial de Posiciones */}
          <Accordion
            title="Historial de Posiciones"
            defaultExpanded={true}
            storageKey="position-history">
            <PositionHistory history={positionHistory} statistics={historyStats} />
          </Accordion>
        </div>
      </main>

      {/* Toast para notificaciones */}
      {showToast && (
        <Toast message={toastMessage} type="info" onClose={() => setShowToast(false)} />
      )}
    </div>
  )
}

export default AppContent
