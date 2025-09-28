import React, { useCallback, useEffect, useRef, useState } from 'react'
import CandlestickChart from '../CandlestickChart'
import { useBinanceKlines, useBinanceSocket } from './hooks'
import './styles.css'
import type { ChartWrapperProps } from './types'

const ChartWrapper: React.FC<ChartWrapperProps> = ({
  symbol = 'DOGEUSDT',
  live = true,
  binanceSymbol = 'DOGEUSDT',
  binanceInterval,
  enableWebSocket = true,
  onData
}) => {
  // Estado para el timeframe con inicialización desde localStorage
  const [timeframe, setTimeframe] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('candlestick-timeframe') || '1m'
    }
    return '1m'
  })

  // Hook para obtener datos históricos de Binance
  const { candlesData, isLoading, error } = useBinanceKlines(symbol, timeframe, 1000)

  // WebSocket propio del componente (autónomo)
  const binanceSocket = useBinanceSocket({
    symbol: binanceSymbol.toLowerCase(),
    interval: timeframe,
    enableKlines: enableWebSocket,
    enableBookTicker: false
  })

  // Estado para forzar re-montado del chart
  const [chartRemountKey, setChartRemountKey] = useState(0)

  // Referencia estable para onData
  const onDataRef = useRef(onData)
  onDataRef.current = onData

  // Emitir datos raw del WebSocket
  useEffect(() => {
    if (binanceSocket.lastMessage && onDataRef.current) {
      onDataRef.current({
        message: 'binance_data',
        data: binanceSocket.lastMessage
      })
    }
  }, [binanceSocket.lastMessage])

  // Emitir estado de conexión
  useEffect(() => {
    if (onDataRef.current) {
      onDataRef.current({
        message: 'connection_state',
        data: {
          isConnected: binanceSocket.isConnected,
          isConnecting: binanceSocket.isConnecting,
          error: binanceSocket.error
        }
      })
    }
  }, [binanceSocket.isConnected, binanceSocket.isConnecting, binanceSocket.error])

  // Función para manejar cambios de timeframe con localStorage
  const handleTimeframeChange = useCallback(
    (newTimeframe: string) => {
      setTimeframe(newTimeframe)

      // Guardar en localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('candlestick-timeframe', newTimeframe)
      }

      // Forzar re-montado cuando cambia el timeframe
      // El WebSocket se reconectará automáticamente con el nuevo intervalo
      setChartRemountKey((prev) => prev + 1)
    },
    [timeframe]
  )

  // Mostrar loading mientras se cargan los datos históricos
  if (isLoading && candlesData.length === 0) {
    return (
      <div className="chart-loading">
        <p>Cargando datos históricos...</p>
      </div>
    )
  }

  // Mostrar error si hay problemas cargando los datos
  if (error && candlesData.length === 0) {
    return (
      <div className="chart-error">
        <p>Error al cargar datos históricos: {error}</p>
      </div>
    )
  }

  return (
    <div className="chart-wrapper">
      <div className="chart-container">
        <CandlestickChart
          key={chartRemountKey}
          symbol={symbol}
          timeframe={timeframe}
          signals={undefined}
          candlesData={candlesData}
          indicatorsData={null}
          onTimeframeChange={handleTimeframeChange}
          live={live && enableWebSocket}
          binanceSymbol={binanceSymbol}
          binanceInterval={binanceInterval || timeframe}
          binanceMsg={binanceSocket.lastMessage}
        />
      </div>
    </div>
  )
}

export default ChartWrapper
