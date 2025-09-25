import type { CandlestickData, LineData } from 'lightweight-charts'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries
} from 'lightweight-charts'
import React, { useEffect, useRef, useState } from 'react'
import { useBinanceSocket } from '../../hooks/useBinanceSocket'
import type { CandlestickChartProps, TechnicalIndicators } from './types'

const TIMEFRAMES = [
  { value: '1m', label: '1m', category: 'Minutos' },
  { value: '3m', label: '3m', category: 'Minutos' },
  { value: '5m', label: '5m', category: 'Minutos' },
  { value: '15m', label: '15m', category: 'Minutos' },
  { value: '30m', label: '30m', category: 'Minutos' },
  { value: '1h', label: '1h', category: 'Horas' },
  { value: '2h', label: '2h', category: 'Horas' },
  { value: '4h', label: '4h', category: 'Horas' },
  { value: '6h', label: '6h', category: 'Horas' },
  { value: '8h', label: '8h', category: 'Horas' },
  { value: '12h', label: '12h', category: 'Horas' },
  { value: '1d', label: '1d', category: 'Días' },
  { value: '3d', label: '3d', category: 'Días' },
  { value: '1w', label: '1w', category: 'Semanas' },
  { value: '1M', label: '1M', category: 'Meses' }
]

// Ultra-simple test data to avoid assertion errors
const generateSimpleData = (): CandlestickData[] => {
  const data: CandlestickData[] = []
  const baseTime = Math.floor(Date.now() / 1000)
  for (let i = 0; i < 20; i++) {
    const time = baseTime - (20 - i) * 60
    const basePrice = 50000 + i * 10
    data.push({
      time: time as any,
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
  onTimeframeChange,
  live = false,
  binanceSymbol,
  binanceInterval
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

  const { lastMessage: binanceMsg } = useBinanceSocket(
    live
      ? {
          symbol: (binanceSymbol || symbol).toLowerCase(),
          interval: (binanceInterval || timeframe).toLowerCase(),
          enableKlines: true,
          enableBookTicker: false
        }
      : { enableKlines: false, enableBookTicker: false }
  )

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

  useEffect(() => {
    if (!live && propCandlesData && Array.isArray(propCandlesData) && propCandlesData.length > 0) {
      const formattedData: CandlestickData[] = propCandlesData.map((candle: any) => ({
        time: (candle.time / 1000) as any,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close
      }))
      setCandleData(formattedData)
    }
  }, [propCandlesData, live])

  useEffect(() => {
    if (!live && propIndicatorsData) {
      setIndicators(propIndicatorsData)
    }
  }, [propIndicatorsData, live])

  useEffect(() => {
    if (!live || !binanceMsg) return
    try {
      if (binanceMsg.type === 'binance.kline' && binanceMsg.data) {
        const klineWrapper = binanceMsg.data
        const k = klineWrapper.k || klineWrapper
        const startMs = k.t ?? k.startTime
        const open = Number(k.o ?? k.open)
        const high = Number(k.h ?? k.high)
        const low = Number(k.l ?? k.low)
        const close = Number(k.c ?? k.close)
        const volume = Number(k.v ?? k.volume ?? 0)

        const newCandle: CandlestickData & { volume?: number; ms?: number } = {
          time: Math.floor((startMs as number) / 1000) as any,
          open,
          high,
          low,
          close
        }

        setCandleData((prev) => {
          const next = [...prev]
          const targetTime = Math.floor((startMs as number) / 1000)
          const idx = next.findIndex((c) => (c.time as number) === targetTime)
          if (idx >= 0) next[idx] = newCandle
          else next.push(newCandle)
          const trimmed = next.slice(-500)

          // Forzar redibujo completo para comprobar animación
          if (seriesRef.current) {
            seriesRef.current.setData(trimmed)
          }

          const closes = trimmed.map((c) => c.close)
          const timesMs = trimmed.map((c) => ((c.time as number) * 1000) as number)
          const smaFast = computeSMA(closes, 8)
          const smaSlow = computeSMA(closes, 21)
          const rsi = computeRSI(closes, 14)
          const volumes = trimmed.map((_, i) => (i === trimmed.length - 1 ? volume : 0))

          setIndicators({
            sma_fast: smaFast.map((v) => (v === null ? NaN : Number(v))),
            sma_slow: smaSlow.map((v) => (v === null ? NaN : Number(v))),
            rsi: rsi.map((v) => (v === null ? NaN : Number(v))),
            volume: volumes,
            timestamps: timesMs
          })

          return trimmed
        })
      }
    } catch (e) {}
  }, [binanceMsg, live])

  useEffect(() => {
    if (!chartContainerRef.current) return
    try {
      const containerWidth = chartContainerRef.current.clientWidth
      const chart = createChart(chartContainerRef.current, {
        width: containerWidth,
        height: 500,
        layout: { background: { type: ColorType.Solid, color: '#1e1e1e' }, textColor: '#d1d4dc' },
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
          borderColor: '#485c7b',
          borderVisible: true,
          visible: true,
          rightOffset: 15,
          tickMarkFormatter: (time: any) => {
            const date = new Date(time * 1000)
            if (timeframe === '1m' || timeframe === '3m' || timeframe === '5m') {
              return date.toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'America/Santiago'
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
            return date.toLocaleString('es-ES', { timeZone: 'America/Santiago' })
          }
        },
        rightPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: { top: 0.05, bottom: 0.05 },
          autoScale: true
        },
        leftPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: { top: 0.05, bottom: 0.05 },
          autoScale: true
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true
        },
        handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
        grid: {
          horzLines: { color: '#2a2e39', style: 1, visible: true },
          vertLines: { color: '#2a2e39', style: 1, visible: true }
        }
      })

      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#26a69a',
        downColor: '#ef5350',
        priceFormat: { type: 'price', precision: 5, minMove: 0.00001 }
      })

      const smaFast = chart.addSeries(LineSeries, {
        color: '#ffff00',
        lineWidth: 1,
        title: 'SMA Fast (8)',
        priceFormat: { type: 'price', precision: 5, minMove: 0.00001 }
      })
      const smaSlow = chart.addSeries(LineSeries, {
        color: '#ff00ff',
        lineWidth: 1,
        title: 'SMA Slow (21)',
        priceFormat: { type: 'price', precision: 5, minMove: 0.00001 }
      })

      const data = candleData.length > 0 ? candleData : generateSimpleData()
      series.setData(data)
      smaFast.setData([])
      smaSlow.setData([])

      if (signals && signals.length > 0) {
        // placeholder para futuros marcadores
      }

      chartRef.current = chart
      seriesRef.current = series
      smaFastRef.current = smaFast
      smaSlowRef.current = smaSlow

      const handleResize = () => {
        if (chartContainerRef.current && chartRef.current) {
          const newWidth = chartContainerRef.current.clientWidth
          chartRef.current.applyOptions({ width: newWidth })
        }
      }
      window.addEventListener('resize', handleResize)
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

  useEffect(() => {
    if (seriesRef.current && candleData.length > 0) {
      seriesRef.current.setData(candleData)
    }
  }, [candleData])

  useEffect(() => {
    if (indicators && smaFastRef.current && smaSlowRef.current) {
      if (
        indicators.sma_fast &&
        Array.isArray(indicators.sma_fast) &&
        indicators.sma_slow &&
        Array.isArray(indicators.sma_slow) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        const smaFastData: LineData[] = indicators.sma_fast
          .map((value, index) => ({ time: (indicators.timestamps[index] / 1000) as any, value }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))
        const smaSlowData: LineData[] = indicators.sma_slow
          .map((value, index) => ({ time: (indicators.timestamps[index] / 1000) as any, value }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))
        smaFastRef.current.setData(smaFastData)
        smaSlowRef.current.setData(smaSlowData)
      }
    }
  }, [indicators])

  useEffect(() => {
    if (rsiContainerRef.current && indicators) {
      if (
        indicators.rsi &&
        Array.isArray(indicators.rsi) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        const rsiChart = createChart(rsiContainerRef.current, {
          width: rsiContainerRef.current.clientWidth,
          height: 200,
          layout: { background: { type: ColorType.Solid, color: '#1e1e1e' }, textColor: '#d1d4dc' },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#485c7b',
            borderVisible: true
          },
          rightPriceScale: {
            borderColor: '#485c7b',
            borderVisible: true,
            scaleMargins: { top: 0.1, bottom: 0.1 }
          }
        })
        const rsiSeries = rsiChart.addSeries(LineSeries, {
          color: '#f39c12',
          lineWidth: 2,
          title: 'RSI'
        })
        const rsiData: LineData[] = indicators.rsi
          .map((value, index) => ({ time: (indicators.timestamps[index] / 1000) as any, value }))
          .filter((item) => item.value !== null && item.value !== undefined && !isNaN(item.value))
        rsiSeries.setData(rsiData)
        const handleResize = () => {
          if (rsiContainerRef.current) {
            rsiChart.applyOptions({ width: rsiContainerRef.current.clientWidth })
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

  useEffect(() => {
    if (volumeContainerRef.current && indicators) {
      if (
        indicators.volume &&
        Array.isArray(indicators.volume) &&
        indicators.timestamps &&
        Array.isArray(indicators.timestamps)
      ) {
        const volumeChart = createChart(volumeContainerRef.current, {
          width: volumeContainerRef.current.clientWidth,
          height: 200,
          layout: { background: { type: ColorType.Solid, color: '#1e1e1e' }, textColor: '#d1d4dc' },
          timeScale: {
            timeVisible: true,
            secondsVisible: false,
            borderColor: '#485c7b',
            borderVisible: true
          },
          rightPriceScale: {
            borderColor: '#485c7b',
            borderVisible: true,
            scaleMargins: { top: 0.1, bottom: 0.1 }
          }
        })
        const volumeSeries = volumeChart.addSeries(HistogramSeries, {
          color: '#9b59b6',
          title: 'Volume'
        })
        const volumeData = indicators.volume.map((value, index) => ({
          time: (indicators.timestamps[index] / 1000) as any,
          value,
          color: value > 0 ? '#26a69a' : '#ef5350'
        }))
        volumeSeries.setData(volumeData)
        const handleResize = () => {
          if (volumeContainerRef.current) {
            volumeChart.applyOptions({ width: volumeContainerRef.current.clientWidth })
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

  useEffect(() => {
    if (seriesRef.current && signals && signals.length > 0) {
      // markers opcionales a futuro
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
        {signals && signals.length > 0 && (
          <div className="signal-overlay">
            {signals.map((signal: any, index: number) => (
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

      {indicators && (
        <div className="indicator-chart-container">
          <div className="indicator-header">
            <h4>RSI (Relative Strength Index)</h4>
          </div>
          <div className="indicator-canvas-container" ref={rsiContainerRef}></div>
        </div>
      )}

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
