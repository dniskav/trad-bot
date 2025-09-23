import type { CandlestickData, LineData } from 'lightweight-charts'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries
} from 'lightweight-charts'
import React, { useEffect, useRef, useState } from 'react'

interface TradingSignal {
  time: number
  type: 'BUY' | 'SELL' | 'HOLD'
  bot: 'conservative' | 'aggressive'
  price: number
  reason?: string
  confidence?: number
}

interface TechnicalIndicators {
  sma_fast: number[]
  sma_slow: number[]
  rsi: number[]
  volume: number[]
  timestamps: number[]
}

interface CandlestickChartProps {
  symbol?: string
  interval?: string
  timeframe?: string
  signals?: TradingSignal[]
  candlesData?: any[]
  indicatorsData?: any
  onTimeframeChange?: (timeframe: string) => void
}

const TIMEFRAMES = [
  // Minutos (intervalo mínimo de Binance)
  { value: '1m', label: '1m', category: 'Minutos' },
  { value: '3m', label: '3m', category: 'Minutos' },
  { value: '5m', label: '5m', category: 'Minutos' },
  { value: '15m', label: '15m', category: 'Minutos' },
  { value: '30m', label: '30m', category: 'Minutos' },

  // Horas
  { value: '1h', label: '1h', category: 'Horas' },
  { value: '2h', label: '2h', category: 'Horas' },
  { value: '4h', label: '4h', category: 'Horas' },
  { value: '6h', label: '6h', category: 'Horas' },
  { value: '8h', label: '8h', category: 'Horas' },
  { value: '12h', label: '12h', category: 'Horas' },

  // Días
  { value: '1d', label: '1d', category: 'Días' },
  { value: '3d', label: '3d', category: 'Días' },

  // Semanas y Meses
  { value: '1w', label: '1w', category: 'Semanas' },
  { value: '1M', label: '1M', category: 'Meses' }
]

// Ultra-simple test data to avoid assertion errors
const generateSimpleData = (): CandlestickData[] => {
  const data: CandlestickData[] = []
  const baseTime = Math.floor(Date.now() / 1000)

  for (let i = 0; i < 20; i++) {
    const time = baseTime - (20 - i) * 60 // 1 minute intervals
    const basePrice = 50000 + i * 10 // Simple ascending trend

    data.push({
      time: time as any, // Type assertion for compatibility
      open: basePrice,
      high: basePrice + 50,
      low: basePrice - 50,
      close: basePrice + (Math.random() - 0.5) * 100
    })
  }

  return data
}

const CandlestickChart: React.FC<CandlestickChartProps> = ({
  symbol = 'BTCUSDT',
  timeframe = '1m',
  signals = [],
  candlesData: propCandlesData = [],
  indicatorsData: propIndicatorsData = null,
  onTimeframeChange
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const rsiContainerRef = useRef<HTMLDivElement>(null)
  const volumeContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const smaFastRef = useRef<any>(null)
  const smaSlowRef = useRef<any>(null)
  const [candleData, setCandleData] = useState<CandlestickData[]>([])
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null)
  // const { lastMessage } = useWebSocketContext() // Ya no necesitamos el contexto

  // Process data from props instead of WebSocket context
  useEffect(() => {
    if (propCandlesData && Array.isArray(propCandlesData) && propCandlesData.length > 0) {
      // Convert server data to chart format
      const formattedData: CandlestickData[] = propCandlesData.map((candle: any) => ({
        time: (candle.time / 1000) as any, // Convert milliseconds to seconds
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }))

      setCandleData(formattedData)
    }
  }, [propCandlesData])

  useEffect(() => {
    if (propIndicatorsData) {
      setIndicators(propIndicatorsData)
    }
  }, [propIndicatorsData])

  useEffect(() => {
    if (!chartContainerRef.current) return

    try {
      // Get container width for responsive design
      const containerWidth = chartContainerRef.current.clientWidth

      // Create chart with proper time formatting
      const chart = createChart(chartContainerRef.current, {
        width: containerWidth,
        height: 500, // Reduced height for main chart only
        layout: {
          background: { type: ColorType.Solid, color: '#1e1e1e' },
          textColor: '#d1d4dc'
        },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#485c7b',
          borderVisible: true,
          visible: true,
          tickMarkFormatter: (time: any) => {
            const date = new Date(time * 1000) // Convert seconds to milliseconds

            // Format based on timeframe
            if (timeframe === '1m' || timeframe === '3m' || timeframe === '5m') {
              return date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'America/Santiago' // Ajustar a tu zona horaria
              })
            } else if (timeframe === '15m' || timeframe === '30m') {
              return date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'America/Santiago'
              })
            } else if (
              timeframe === '1h' ||
              timeframe === '2h' ||
              timeframe === '4h' ||
              timeframe === '6h' ||
              timeframe === '8h' ||
              timeframe === '12h'
            ) {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                timeZone: 'America/Santiago'
              })
            } else if (timeframe === '1d' || timeframe === '3d') {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric',
                timeZone: 'America/Santiago'
              })
            } else if (timeframe === '1w') {
              return date.toLocaleDateString('es-ES', {
                month: 'short',
                day: 'numeric',
                timeZone: 'America/Santiago'
              })
            } else if (timeframe === '1M') {
              return date.toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'short',
                timeZone: 'America/Santiago'
              })
            }

            return date.toLocaleString('es-ES', {
              timeZone: 'America/Santiago'
            })
          }
        },
        rightPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: {
            top: 0.05,
            bottom: 0.05
          },
          autoScale: true
        },
        leftPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: {
            top: 0.05,
            bottom: 0.05
          },
          autoScale: true
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true
        },
        handleScale: {
          axisPressedMouseMove: true,
          mouseWheel: true,
          pinch: true
        },
        grid: {
          horzLines: {
            color: '#2a2e39',
            style: 1,
            visible: true
          },
          vertLines: {
            color: '#2a2e39',
            style: 1,
            visible: true
          }
        }
      })

      // Use the CORRECT v5 API method
      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        priceFormat: {
          type: 'price',
          precision: 5,
          minMove: 0.00001
        }
      })

      // Add SMA lines to main chart
      const smaFast = chart.addSeries(LineSeries, {
        color: '#ffff00', // Yellow - muy visible y diferente
        lineWidth: 3,
        title: 'SMA Fast (8)',
        priceFormat: {
          type: 'price',
          precision: 5,
          minMove: 0.00001
        }
      })

      const smaSlow = chart.addSeries(LineSeries, {
        color: '#ff00ff', // Magenta - muy visible y diferente
        lineWidth: 3,
        title: 'SMA Slow (21)',
        priceFormat: {
          type: 'price',
          precision: 5,
          minMove: 0.00001
        }
      })

      // RSI and Volume will be in separate charts below

      // Use real data if available, otherwise use mock data
      const data = candleData.length > 0 ? candleData : generateSimpleData()

      // Set data
      series.setData(data)

      // Set initial empty data for indicators to avoid errors
      smaFast.setData([])
      smaSlow.setData([])

      // Add signal markers
      if (signals && signals.length > 0) {
        // const markers = signals.map((signal) => ({
        //   time: signal.time as any,
        //   position: signal.type === 'BUY' ? 'belowBar' : 'aboveBar',
        //   color: signal.type === 'BUY' ? '#26a69a' : '#ef5350',
        //   shape: signal.type === 'BUY' ? 'arrowUp' : 'arrowDown',
        //   text: `${signal.bot.toUpperCase()} ${signal.type}`,
        //   size: 1.5,
        //   id: `${signal.bot}-${signal.type}-${signal.time}`,
        //   title: `${signal.bot.toUpperCase()} ${signal.type} Signal`,
        //   description: signal.reason || `${signal.type} signal from ${signal.bot} bot`
        // }))
        // TODO: Implement markers when Lightweight Charts API is clarified
        // try {
        //   // Add markers one by one
        //   markers.forEach(marker => {
        //     series.setMarkers([marker])
        //   })
        // } catch (error) {
        //   console.error('Error adding markers:', error)
        // }
      }

      // Store references
      chartRef.current = chart
      seriesRef.current = series
      smaFastRef.current = smaFast
      smaSlowRef.current = smaSlow

      // Handle resize
      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          const newWidth = chartContainerRef.current.clientWidth
          chartRef.current.applyOptions({ width: newWidth })
        }
      }

      window.addEventListener('resize', handleResize)

      // Cleanup
      return () => {
        window.removeEventListener('resize', handleResize)
        if (chartRef.current) {
          chartRef.current.remove()
          chartRef.current = null
        }
      }
    } catch (error) {
      console.error('❌ CandlestickChart: Error creando gráfico:', error)
    }
  }, [timeframe, candleData, indicators])

  // Update chart when new data arrives
  useEffect(() => {
    if (seriesRef.current && candleData.length > 0) {
      seriesRef.current.setData(candleData)
    }
  }, [candleData])

  // Update indicators when new data arrives
  useEffect(() => {
    if (indicators && smaFastRef.current && smaSlowRef.current) {
      // Verificar que los datos de indicadores existan y sean arrays
      if (
        indicators.sma_fast &&
        Array.isArray(indicators.sma_fast) &&
        indicators.sma_slow &&
        Array.isArray(indicators.sma_slow) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        // Prepare SMA data - filter out null values
        const smaFastData: LineData[] = indicators.sma_fast
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value: value
          }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))

        const smaSlowData: LineData[] = indicators.sma_slow
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value: value
          }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))

        // Update SMA series
        smaFastRef.current.setData(smaFastData)
        smaSlowRef.current.setData(smaSlowData)
      }
    }
  }, [indicators])

  // Create RSI chart
  useEffect(() => {
    if (rsiContainerRef.current && indicators) {
      // Verificar que los datos de RSI existan
      if (
        indicators.rsi &&
        Array.isArray(indicators.rsi) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        const rsiChart = createChart(rsiContainerRef.current, {
          width: rsiContainerRef.current.clientWidth,
          height: 200,
          layout: {
            background: { type: ColorType.Solid, color: '#1e1e1e' },
            textColor: '#d1d4dc'
          },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#485c7b',
            borderVisible: true
          },
          rightPriceScale: {
            borderColor: '#485c7b',
            borderVisible: true,
            scaleMargins: {
              top: 0.1,
              bottom: 0.1
            }
          }
        })

        const rsiSeries = rsiChart.addSeries(LineSeries, {
          color: '#f39c12',
          lineWidth: 2,
          title: 'RSI'
        })

        // Prepare RSI data - filter out null values
        const rsiData: LineData[] = indicators.rsi
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value: value
          }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))

        rsiSeries.setData(rsiData)

        // Handle resize
        const handleResize = () => {
          if (rsiContainerRef.current) {
            rsiChart.applyOptions({
              width: rsiContainerRef.current.clientWidth
            })
          }
        }

        window.addEventListener('resize', handleResize)
        return () => {
          window.removeEventListener('resize', handleResize)
          rsiChart.remove()
        }
      }
    }
  }, [indicators])

  // Create Volume chart
  useEffect(() => {
    if (volumeContainerRef.current && indicators) {
      // Verificar que los datos de Volume existan
      if (
        indicators.volume &&
        Array.isArray(indicators.volume) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        const volumeChart = createChart(volumeContainerRef.current, {
          width: volumeContainerRef.current.clientWidth,
          height: 200,
          layout: {
            background: { type: ColorType.Solid, color: '#1e1e1e' },
            textColor: '#d1d4dc'
          },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#485c7b',
            borderVisible: true
          },
          rightPriceScale: {
            borderColor: '#485c7b',
            borderVisible: true,
            scaleMargins: {
              top: 0.1,
              bottom: 0.1
            }
          }
        })

        const volumeSeries = volumeChart.addSeries(HistogramSeries, {
          color: '#9b59b6',
          title: 'Volume'
        })

        // Prepare Volume data
        const volumeData = indicators.volume.map((value, index) => ({
          time: (indicators.timestamps[index] / 1000) as any,
          value: value,
          color: value > 0 ? '#26a69a' : '#ef5350'
        }))

        volumeSeries.setData(volumeData)

        // Handle resize
        const handleResize = () => {
          if (volumeContainerRef.current) {
            volumeChart.applyOptions({
              width: volumeContainerRef.current.clientWidth
            })
          }
        }

        window.addEventListener('resize', handleResize)
        return () => {
          window.removeEventListener('resize', handleResize)
          volumeChart.remove()
        }
      }
    }
  }, [indicators])

  // Update signals when they change
  useEffect(() => {
    if (seriesRef.current && signals && signals.length > 0) {
      // const markers = signals.map((signal) => ({
      //   time: signal.time as any,
      //   position: signal.type === 'BUY' ? 'belowBar' : 'aboveBar',
      //   color: signal.type === 'BUY' ? '#26a69a' : '#ef5350',
      //   shape: signal.type === 'BUY' ? 'arrowUp' : 'arrowDown',
      //   text: `${signal.bot.toUpperCase()} ${signal.type}`,
      //   size: 1.5,
      //   id: `${signal.bot}-${signal.type}-${signal.time}`,
      //   // Add more detailed information
      //   title: `${signal.bot.toUpperCase()} ${signal.type} Signal`,
      //   description: signal.reason || `${signal.type} signal from ${signal.bot} bot`
      // }))
      // TODO: Implement markers when Lightweight Charts API is clarified
      // try {
      //   // Clear existing markers first
      //   seriesRef.current.setMarkers([])
      //   // Add markers one by one
      //   markers.forEach(marker => {
      //     seriesRef.current.setMarkers([marker])
      //   })
      // } catch (error) {
      //   console.error('Error updating markers:', error)
      // }
    }
  }, [signals])

  return (
    <div className="candlestick-chart">
      <div className="chart-header">
        <h3>
          {symbol} - {timeframe}
        </h3>
        <div className="chart-info">
          <span>{candleData.length > 0 ? 'Real Data' : 'Test Data'}</span>
          <span>•</span>
          <span>{candleData.length > 0 ? `${candleData.length} candles` : '20 candles'}</span>
          <span>•</span>
          <span>Props: {propCandlesData?.length || 0} velas recibidas</span>
          {indicators && (
            <>
              <span>•</span>
              <span>Indicadores: SMA, RSI, Volumen</span>
            </>
          )}
          {signals && signals.length > 0 && (
            <>
              <span>•</span>
              <span>{signals.length} signals</span>
            </>
          )}
        </div>
      </div>

      {/* Timeframe Selector */}
      {onTimeframeChange && (
        <div className="timeframe-selector">
          <div className="timeframe-header">
            <h4>Timeframe</h4>
          </div>
          <div className="timeframe-buttons">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                className={`timeframe-btn ${timeframe === tf.value ? 'active' : ''}`}
                onClick={() => onTimeframeChange(tf.value)}
                title={`${tf.label} - ${tf.category}${tf.value === '1m' ? ' (Mínimo)' : ''}`}>
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="chart-legend">
        {indicators && (
          <>
            <div className="legend-item">
              <div className="legend-marker" style={{ backgroundColor: '#ffff00' }}></div>
              <span>SMA Fast (8)</span>
            </div>
            <div className="legend-item">
              <div className="legend-marker" style={{ backgroundColor: '#ff00ff' }}></div>
              <span>SMA Slow (21)</span>
            </div>
            <div className="legend-item">
              <div className="legend-marker" style={{ backgroundColor: '#f39c12' }}></div>
              <span>RSI</span>
            </div>
            <div className="legend-item">
              <div className="legend-marker" style={{ backgroundColor: '#9b59b6' }}></div>
              <span>Volumen</span>
            </div>
          </>
        )}
        {signals && signals.length > 0 && (
          <>
            <div className="legend-item">
              <div className="legend-marker buy"></div>
              <span>BUY Signal</span>
            </div>
            <div className="legend-item">
              <div className="legend-marker sell"></div>
              <span>SELL Signal</span>
            </div>
          </>
        )}
      </div>
      <div className="chart-container">
        <div ref={chartContainerRef} className="chart-canvas-container" />
        {/* Signal Overlay */}
        {signals && signals.length > 0 && (
          <div className="signal-overlay">
            {signals.map((signal, index) => (
              <div
                key={`${signal.bot}-${signal.type}-${signal.time}-${index}`}
                className={`signal-marker ${signal.type.toLowerCase()} ${signal.bot}`}
                title={`${signal.bot.toUpperCase()} ${signal.type} - ${
                  signal.reason || 'Trading Signal'
                }`}>
                <div className="signal-icon">{signal.type === 'BUY' ? '▲' : '▼'}</div>
                <div className="signal-label">{signal.bot === 'conservative' ? 'C' : 'A'}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* RSI Chart */}
      {indicators && (
        <div className="indicator-chart-container">
          <div className="indicator-header">
            <h4>RSI (Relative Strength Index)</h4>
          </div>
          <div className="indicator-canvas-container" ref={rsiContainerRef}></div>
        </div>
      )}

      {/* Volume Chart */}
      {indicators && (
        <div className="indicator-chart-container">
          <div className="indicator-header">
            <h4>Volumen</h4>
          </div>
          <div className="indicator-canvas-container" ref={volumeContainerRef}></div>
        </div>
      )}
      <div className="chart-footer">
        <small>Lightweight Charts - {candleData.length > 0 ? 'Real-time Data' : 'Test Data'}</small>
        {signals && signals.length > 0 && (
          <div className="signal-info">
            <small>💡 Hover over signals for details</small>
          </div>
        )}
      </div>
    </div>
  )
}

export default CandlestickChart
