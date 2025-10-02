import type { CandlestickData, LineData } from 'lightweight-charts'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries
} from 'lightweight-charts'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Accordion } from '../Accordion'
import { useBinanceSocket, useVolumeData } from '../ChartWrapper/hooks'
import type { CandlestickChartProps, TechnicalIndicators } from './types'
import {
  filterVolumeDataForChart,
  processHistoricalVolume,
  processWebSocketVolume,
  validateVolumeData
} from './utils'

// Extender CandlestickData para incluir volumen
interface ExtendedCandlestickData extends CandlestickData {
  volume?: number
}

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
  // Generar un ID único para este componente para evitar duplicados
  const componentId = useMemo(() => `chart-${Math.random().toString(36).substr(2, 9)}`, [])

  // Estado local para persistencia del timeframe
  const [localTimeframe, setLocalTimeframe] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('candlestick-timeframe') || timeframe
    }
    return timeframe
  })

  // Función para manejar el cambio de timeframe
  const handleTimeframeChange = (newTimeframe: string) => {
    setLocalTimeframe(newTimeframe)
    // Guardar en localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('candlestick-timeframe', newTimeframe)
    }
    // Llamar al callback del padre
    if (onTimeframeChange) {
      onTimeframeChange(newTimeframe)
    }
  }

  // Función para obtener información detallada de los indicadores
  const getIndicatorsInfo = () => {
    if (!indicators) return null

    const availableIndicators = []
    if (indicators.sma_fast && indicators.sma_fast.length > 0) availableIndicators.push('SMA(8,21)')
    if (indicators.rsi && indicators.rsi.length > 0) availableIndicators.push('RSI')
    if (indicators.volume && indicators.volume.length > 0) availableIndicators.push('Volumen')
    if (indicators.macd && indicators.macd.macd && indicators.macd.macd.length > 0)
      availableIndicators.push('MACD')

    return availableIndicators.length > 0 ? availableIndicators.join(', ') : null
  }

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const rsiContainerRef = useRef<HTMLDivElement>(null)
  const volumeContainerRef = useRef<HTMLDivElement>(null)
  const macdContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const seriesInitializedRef = useRef<boolean>(false)
  const smaFastRef = useRef<any>(null)
  const smaSlowRef = useRef<any>(null)
  const [candleData, setCandleData] = useState<ExtendedCandlestickData[]>([])
  const [indicators, setIndicators] = useState<TechnicalIndicators | null>(null)
  const [, setUserHasZoomed] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('chart-zoom-state')
      return saved === 'true'
    }
    return false
  })
  const [, setSavedVisibleRange] = useState<{ from: number; to: number } | null>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('chart-visible-range')
      return saved ? JSON.parse(saved) : null
    }
    return null
  })

  // Hook personalizado para manejar datos de volumen
  const { volumeData, updateVolumeData, clearVolumeData, setVolumeType } = useVolumeData()

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

  // Sincronizar con el prop cuando cambie
  useEffect(() => {
    setLocalTimeframe(timeframe)
    // Limpiar indicadores y volumen cuando cambia el timeframe para evitar mezcla de datos
    setIndicators(null)
    clearVolumeData()
  }, [timeframe, clearVolumeData])

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

  const computeEMA = (values: number[], period: number): (number | null)[] => {
    const k = 2 / (period + 1)
    const ema: (number | null)[] = new Array(values.length).fill(null)
    if (values.length < period) return ema
    // SMA inicial
    let sum = 0
    for (let i = 0; i < period; i++) sum += values[i]
    let prev = sum / period
    ema[period - 1] = prev
    for (let i = period; i < values.length; i++) {
      const v = values[i]
      prev = v * k + prev * (1 - k)
      ema[i] = prev
    }
    return ema
  }

  const computeMACD = (closes: number[]) => {
    const ema12 = computeEMA(closes, 12)
    const ema26 = computeEMA(closes, 26)
    const macd: (number | null)[] = closes.map((_, i) =>
      ema12[i] != null && ema26[i] != null ? (ema12[i] as number) - (ema26[i] as number) : null
    )
    const macdValues = macd.map((v) => (v == null ? 0 : (v as number)))
    const signal = computeEMA(macdValues, 9)
    const histogram: (number | null)[] = macd.map((v, i) =>
      v != null && signal[i] != null ? (v as number) - (signal[i] as number) : null
    )
    return { macd, signal, histogram }
  }

  useEffect(() => {
    if (propCandlesData && Array.isArray(propCandlesData) && propCandlesData.length > 0) {
      const formattedData: ExtendedCandlestickData[] = propCandlesData
        .map((candle: any) => ({
          time: (candle.time / 1000) as any, // Convertir de ms a segundos para Lightweight Charts
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
          volume: candle.volume || 0
        }))
        .filter((candle) => {
          // Validar que el tiempo sea válido y no sea NaN
          const time = candle.time as number
          return !isNaN(time) && isFinite(time) && time > 0
        })
        .sort((a, b) => (a.time as number) - (b.time as number)) // Ordenar por tiempo ascendente

      setCandleData(formattedData)
    }
  }, [propCandlesData, timeframe])

  // useEffect separado para procesar datos históricos de volumen
  useEffect(() => {
    if (candleData && candleData.length > 0 && !volumeData) {
      const { volumes, timestamps } = processHistoricalVolume(candleData)

      if (validateVolumeData(volumes, timestamps)) {
        updateVolumeData(volumes, timestamps)
      } else {
        console.warn('⚠️ Datos de volumen históricos inválidos')
      }
    }
  }, [candleData, volumeData, updateVolumeData])

  useEffect(() => {
    if (propIndicatorsData) {
      setIndicators(propIndicatorsData)
    } else if (candleData && candleData.length > 0 && !indicators) {
      // Solo crear indicadores básicos si no existen indicadores previos
      // Esto evita sobrescribir indicadores calculados en tiempo real

      // Calcular indicadores técnicos desde los datos históricos
      const closes = candleData.map((candle) => candle.close)
      const timestamps = candleData.map((candle) => (candle.time as number) * 1000)
      const smaFast = computeSMA(closes, 8)
      const smaSlow = computeSMA(closes, 21)
      const rsi = computeRSI(closes, 14)

      const basicIndicators: TechnicalIndicators = {
        volume: [],
        timestamps: timestamps,
        sma_fast: smaFast.map((v) => (v === null ? NaN : Number(v))),
        sma_slow: smaSlow.map((v) => (v === null ? NaN : Number(v))),
        rsi: rsi.map((v) => (v === null ? NaN : Number(v)))
      }

      setIndicators(basicIndicators)
    }
  }, [propIndicatorsData, candleData, timeframe, indicators])

  useEffect(() => {
    if (!live || !binanceMsg) return
    try {
      if (binanceMsg.type === 'binance.kline' && binanceMsg.data) {
        const klineWrapper = binanceMsg.data
        const k = klineWrapper.k || klineWrapper

        // Verificar que el intervalo del WebSocket coincida con el timeframe actual
        const wsInterval = k.i ?? k.interval
        if (wsInterval !== timeframe) {
          return
        }

        const startMs = k.t ?? k.startTime
        const open = Number(k.o ?? k.open)
        const high = Number(k.h ?? k.high)
        const low = Number(k.l ?? k.low)
        const close = Number(k.c ?? k.close)
        // Usar volumen en moneda cotizada (quote) para mejor comparabilidad
        const volume = Number(k.q ?? k.quoteVolume ?? k.v ?? k.volume ?? 0)

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

          // Animación óptima: update si existe, setData si es nueva
          if (seriesRef.current) {
            if (!seriesInitializedRef.current) {
              seriesRef.current.setData(trimmed)
              seriesInitializedRef.current = true
            } else if (idx >= 0) {
              seriesRef.current.update(newCandle)
            } else {
              seriesRef.current.setData(trimmed)
            }
          }

          const closes = trimmed.map((c) => c.close)
          const smaFast = computeSMA(closes, 8)
          const smaSlow = computeSMA(closes, 21)
          const rsi = computeRSI(closes, 14)
          const macdObj = computeMACD(closes)

          // Procesar volumen usando las nuevas utilidades
          const currentVolumes = volumeData?.volume || []
          const currentTimestamps = volumeData?.timestamps || []
          const newTimestamp = Math.floor((startMs as number) / 1000) * 1000

          const { volumes, timestamps } = processWebSocketVolume(
            volume,
            currentVolumes,
            currentTimestamps,
            newTimestamp
          )

          // Actualizar datos de volumen
          updateVolumeData(volumes, timestamps)

          // Solo actualizar indicadores si no existen o si hay datos suficientes
          setIndicators((prev) => {
            // Si no hay indicadores previos, crear nuevos
            if (!prev) {
              return {
                sma_fast: smaFast.map((v) => (v === null ? NaN : Number(v))),
                sma_slow: smaSlow.map((v) => (v === null ? NaN : Number(v))),
                rsi: rsi.map((v) => (v === null ? NaN : Number(v))),
                volume: volumes,
                timestamps: timestamps,
                macd: {
                  macd: macdObj.macd.map((v) => (v === null ? NaN : Number(v))) as number[],
                  signal: macdObj.signal.map((v) => (v === null ? NaN : Number(v))) as number[],
                  histogram: macdObj.histogram.map((v) =>
                    v === null ? NaN : Number(v)
                  ) as number[]
                }
              }
            }

            // Si ya existen indicadores, solo actualizar volumen y timestamps
            // Mantener SMA, RSI y MACD existentes para evitar parpadeo
            return {
              ...prev,
              volume: volumes,
              timestamps: timestamps
            }
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
          rightOffset: 0,
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
          scaleMargins: { top: 0.15, bottom: 0.05 },
          autoScale: true,
          alignLabels: false
        },
        leftPriceScale: {
          borderColor: '#485c7b',
          borderVisible: true,
          scaleMargins: { top: 0.15, bottom: 0.05 },
          autoScale: true,
          alignLabels: false
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

      // Listener para detectar zoom manual del usuario (con delay para evitar errores)
      setTimeout(() => {
        try {
          chart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
            if (timeRange && timeRange.from !== null && timeRange.to !== null) {
              setUserHasZoomed(true)
              setSavedVisibleRange({
                from: timeRange.from as number,
                to: timeRange.to as number
              })

              // Guardar en localStorage
              if (typeof window !== 'undefined') {
                localStorage.setItem('chart-zoom-state', 'true')
                localStorage.setItem(
                  'chart-visible-range',
                  JSON.stringify({
                    from: timeRange.from as number,
                    to: timeRange.to as number
                  })
                )
              }
            }
          })
        } catch (error) {
          console.error('❌ Error al suscribirse al cambio de rango visible:', error)
        }
      }, 100)

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
      seriesInitializedRef.current = false
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
  }, [timeframe])

  useEffect(() => {
    // Solo procesar datos si el chart está inicializado y hay datos válidos
    if (chartRef.current && seriesRef.current && candleData.length > 0) {
      try {
        seriesRef.current.setData(candleData)
        seriesInitializedRef.current = true
      } catch (error) {
        console.error('❌ Error al establecer datos en el chart:', error)
      }
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
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value
          }))
          .filter((item) => {
            const time = item.time as number
            return (
              item.value !== null &&
              item.value !== undefined &&
              !isNaN(item.value) &&
              !isNaN(time) &&
              isFinite(time) &&
              time > 0
            )
          })
        const smaSlowData: LineData[] = indicators.sma_slow
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value
          }))
          .filter((item) => {
            const time = item.time as number
            return (
              item.value !== null &&
              item.value !== undefined &&
              !isNaN(item.value) &&
              !isNaN(time) &&
              isFinite(time) &&
              time > 0
            )
          })
        smaFastRef.current.setData(smaFastData)
        smaSlowRef.current.setData(smaSlowData)
      }
    }
  }, [indicators])

  // MACD sub-chart
  useEffect(() => {
    if (macdContainerRef.current && indicators && indicators.macd) {
      const { macd, signal, histogram } = indicators.macd
      if (
        Array.isArray(macd) &&
        Array.isArray(signal) &&
        Array.isArray(histogram) &&
        Array.isArray(indicators.timestamps)
      ) {
        const macdChart = createChart(macdContainerRef.current, {
          width: macdContainerRef.current.clientWidth,
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

        const macdLine = macdChart.addSeries(LineSeries, {
          color: '#00bcd4',
          lineWidth: 1,
          title: 'MACD',
          priceFormat: { type: 'price', precision: 6, minMove: 0.000001 }
        })
        const signalLine = macdChart.addSeries(LineSeries, {
          color: '#e67e22',
          lineWidth: 1,
          title: 'Signal',
          priceFormat: { type: 'price', precision: 6, minMove: 0.000001 }
        })
        const histSeries = macdChart.addSeries(HistogramSeries, {
          title: 'Histogram',
          priceFormat: { type: 'price', precision: 6, minMove: 0.000001 }
        })

        const macdData: LineData[] = macd
          .map((v, i) => ({
            time: (indicators.timestamps[i] / 1000) as any,
            value: v as number
          }))
          .filter((p) => {
            const time = p.time as number
            return Number.isFinite(p.value) && !isNaN(time) && isFinite(time) && time > 0
          })
        const signalData: LineData[] = signal
          .map((v, i) => ({
            time: (indicators.timestamps[i] / 1000) as any,
            value: v as number
          }))
          .filter((p) => {
            const time = p.time as number
            return Number.isFinite(p.value) && !isNaN(time) && isFinite(time) && time > 0
          })
        const histData = histogram
          .map((v, i) => ({
            time: (indicators.timestamps[i] / 1000) as any,
            value: Number.isFinite(v as number) ? (v as number) : 0,
            color: (v as number) >= 0 ? '#26a69a' : '#ef5350'
          }))
          .filter((p) => {
            const time = p.time as number
            return !isNaN(time) && isFinite(time) && time > 0
          })

        macdLine.setData(macdData)
        signalLine.setData(signalData)
        histSeries.setData(histData)

        const handleResize = () => {
          if (macdContainerRef.current) {
            macdChart.applyOptions({ width: macdContainerRef.current.clientWidth })
          }
        }
        window.addEventListener('resize', handleResize)
        return () => {
          window.removeEventListener('resize', handleResize)
          macdChart.remove()
        }
      }
    }
  }, [indicators])

  // If indicators from props do not include MACD, compute it from closes
  useEffect(() => {
    if (!indicators || indicators.macd) return
    if (candleData.length === 0) return
    const closes = candleData.map((c) => c.close)
    const timesMs = candleData.map((c) => ((c.time as number) * 1000) as number)
    const macdObj = computeMACD(closes)
    setIndicators((prev) =>
      prev
        ? {
            ...prev,
            timestamps:
              prev.timestamps && prev.timestamps.length === timesMs.length
                ? prev.timestamps
                : timesMs,
            macd: {
              macd: macdObj.macd.map((v) => (v === null ? NaN : Number(v))) as number[],
              signal: macdObj.signal.map((v) => (v === null ? NaN : Number(v))) as number[],
              histogram: macdObj.histogram.map((v) => (v === null ? NaN : Number(v))) as number[]
            }
          }
        : prev
    )
  }, [candleData, indicators])

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
          .map((value, index) => ({
            time: (indicators.timestamps[index] / 1000) as any,
            value
          }))
          .filter((item) => {
            const time = item.time as number
            return (
              item.value !== null &&
              item.value !== undefined &&
              !isNaN(item.value) &&
              !isNaN(time) &&
              isFinite(time) &&
              time > 0
            )
          })
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

  // useEffect separado para el chart de volumen
  useEffect(() => {
    if (volumeContainerRef.current && volumeData) {
      const { volume: volumes, timestamps } = volumeData

      if (!validateVolumeData(volumes, timestamps)) {
        console.warn('⚠️ Datos de volumen inválidos para el chart')
        return
      }

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
        title: 'Volume'
      })

      const chartData = filterVolumeDataForChart(volumes, timestamps, candleData)
      volumeSeries.setData(chartData)

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
  }, [volumeData])

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
          {live && (
            <>
              <span>•</span>
              <span style={{ color: '#26a69a' }}>Live: {binanceSymbol?.toUpperCase()}</span>
            </>
          )}
          {getIndicatorsInfo() && (
            <>
              <span>•</span>
              <span>Indicadores: {getIndicatorsInfo()}</span>
            </>
          )}
          {signals && signals.length > 0 && (
            <>
              <span>•</span>
              <span>{signals.length} signals</span>
            </>
          )}
          <span>•</span>
          <button
            id={`${componentId}-volume-toggle`}
            className="timeframe-btn"
            onClick={() => setVolumeType(volumeData?.volumeType === 'quote' ? 'base' : 'quote')}
            title="Alternar tipo de volumen (quote/base)">
            Vol: {volumeData?.volumeType || 'quote'}
          </button>
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
                id={`${componentId}-timeframe-${tf.value}`}
                className={`timeframe-btn ${localTimeframe === tf.value ? 'active' : ''}`}
                onClick={() => handleTimeframeChange(tf.value)}
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
              <span style={{ marginLeft: 8, opacity: 0.8 }}>({timeframe})</span>
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

      <Accordion title="Gráfico de Velas" defaultExpanded={true} storageKey="chart-candles">
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
      </Accordion>

      {indicators && (
        <Accordion title="RSI" defaultExpanded={false} storageKey="chart-rsi">
          <div className="indicator-chart-container">
            <div className="indicator-canvas-container" ref={rsiContainerRef}></div>
          </div>
        </Accordion>
      )}

      {volumeData && (
        <Accordion
          title={`Volumen (${volumeData.volumeType})`}
          defaultExpanded={false}
          storageKey="chart-volume">
          <div className="indicator-chart-container">
            <div className="indicator-canvas-container" ref={volumeContainerRef}></div>
          </div>
        </Accordion>
      )}

      {indicators && indicators.macd && (
        <Accordion title="MACD" defaultExpanded={false} storageKey="chart-macd">
          <div className="indicator-chart-container">
            <div className="indicator-canvas-container" ref={macdContainerRef}></div>
          </div>
        </Accordion>
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
