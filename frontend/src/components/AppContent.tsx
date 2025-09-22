import React, { useContext, useEffect, useState } from 'react'
import { WebSocketContext } from '../contexts/WebSocketContext'
// import { useSocket } from '../hooks/useSocket'
import Accordion from './Accordion'
import AccountBalance from './AccountBalance'
import ActivePositions from './ActivePositions'
import BotSignals from './BotSignals'
import CandlestickChart from './CandlestickChart'
import MarginInfo from './MarginInfo'
import PlugAndPlayBots from './PlugAndPlayBots'
import PositionHistory from './PositionHistory'
import Toast from './Toast'
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
  const [activePositions, setActivePositions] = useState<any[]>([])
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [accountBalance, setAccountBalance] = useState<any>(null)
  const [marginInfo, setMarginInfo] = useState<any>(null)
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
  // console.log('🔌 AppContent: ctx obtenido con useContext:', ctx) // Comentado para reducir spam

  // Efecto para procesar mensajes del contexto
  useEffect(() => {
    // console.log('📨 AppContent: Efecto ejecutado, ctx:', ctx, 'lastMessage:', ctx?.lastMessage)
    if (ctx && ctx.lastMessage) {
      const data = ctx.lastMessage.message
      // console.log('📨 AppContent: Procesando mensaje del contexto:', data)
      // console.log('📨 AppContent: Tipo de mensaje:', data?.type)
      // console.log('📨 AppContent: Datos del mensaje:', data?.data)

      // Procesar diferentes tipos de mensajes
      if (data.type === 'bot_signals') {
        setBotSignals(data.data || [])
      } else if (data.type === 'position_history') {
        setPositionHistory(data.data || [])
      } else if (data.type === 'active_positions') {
        setActivePositions(data.data || [])
      } else if (data.type === 'price' || data.type === 'price_update') {
        setCurrentPrice(data.data?.price || 0)
      } else if (data.type === 'account_balance') {
        setAccountBalance(data.data)
      } else if (data.type === 'margin_info') {
        setMarginInfo(data.data)
      } else if (data.type === 'candles') {
        // Datos de velas para el gráfico
        // console.log('📊 AppContent: === PROCESANDO DATOS DE VELAS ===')
        // console.log('📊 AppContent: data.data:', data.data)
        // console.log('📊 AppContent: data.data.candles:', data.data?.candles)
        // console.log('📊 AppContent: data.data.candles.length:', data.data?.candles?.length)
        // console.log(
        //   '📊 AppContent: Datos de velas recibidos desde contexto:',
        //   data.data?.candles?.length || 0,
        //   'velas'
        // )
        // console.log('📊 AppContent: Estructura de datos de velas desde contexto:', data.data)
        setCandlesData(data.data?.candles || [])
        console.log('📊 AppContent: setCandlesData llamado con:', data.data?.candles || [])

        // Procesar bot_signals si están disponibles
        if (data.data?.bot_signals) {
          // console.log('🤖 AppContent: Procesando bot_signals:', data.data.bot_signals)
          setBotSignals(data.data.bot_signals)

          // Extraer historial de posiciones si viene embebido en la carga de velas
          const positionsPayload = data.data?.bot_signals?.positions
          const historyFromPayload = positionsPayload?.history
          if (Array.isArray(historyFromPayload)) {
            setPositionHistory(historyFromPayload)
            // Calcular estadísticas dinámicas por bot
            const stats = calculateStatistics(historyFromPayload)
            setHistoryStats(stats)
          }
          // Extraer posiciones activas si vienen embebidas (compatibilidad)
          const activeFromPayload = positionsPayload?.active_positions
          if (activeFromPayload) {
            setActivePositions(activeFromPayload)
          }
        }
      } else if (data.type === 'indicators') {
        // Datos de indicadores para el gráfico
        // console.log(
        //   '📈 AppContent: Datos de indicadores recibidos desde contexto:',
        //   Object.keys(data.data || {})
        // )
        // console.log('📈 AppContent: Estructura de datos de indicadores desde contexto:', data.data)
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
  //     // console.log('📤 AppContent: Mensaje enviado a través del WebSocket:', message) // Comentado para reducir spam

  //     // También actualizar el contexto para mantener compatibilidad
  //     if (ctx) {
  //       ctx.addMessage('sent', message)
  //     }
  //   } else {
  //     // console.warn('⚠️ AppContent: No se puede enviar mensaje, WebSocket no conectado') // Comentado para reducir spam
  //     setToastMessage('No se puede enviar mensaje: WebSocket no conectado')
  //     setShowToast(true)
  //   }
  // }

  // Función para cambiar timeframe
  const handleTimeframeChange = (newTimeframe: string) => {
    onTimeframeChange(newTimeframe)
    // El AppSetup manejará la reconexión
  }

  // Fallback: cargar velas iniciales vía REST si aún no han llegado por WS
  useEffect(() => {
    let cancelled = false
    const loadInitialCandles = async () => {
      try {
        const res = await fetch(
          `/klines?symbol=DOGEUSDT&interval=${encodeURIComponent(timeframe)}&limit=500`
        )
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          setCandlesData(data)
        }
      } catch (_) {
        // Ignorar errores del fallback
      }
    }
    // Si no tenemos velas aún, intenta cargar
    if (!candlesData || candlesData.length === 0) {
      loadInitialCandles()
    }
    return () => {
      cancelled = true
    }
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
            <ActivePositions
              positions={
                (botSignals?.positions?.active_positions as any) || (activePositions as any)
              }
            />
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
            />
          </Accordion>

          {/* Plugin Bots */}
          <Accordion title="Plugin Bots" defaultExpanded={true} storageKey="plugin-bots">
            <PlugAndPlayBots
              history={positionHistory}
              activePositions={botSignals?.positions?.active_positions}
            />
          </Accordion>

          {/* Historial de Posiciones */}
          <Accordion
            title="Historial de Posiciones"
            defaultExpanded={false}
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
