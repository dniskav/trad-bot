// Utilidades para procesamiento de datos de volumen

export interface VolumeProcessingResult {
  volumes: number[]
  timestamps: number[]
}

/**
 * Procesa datos de volumen desde velas históricas
 */
export const processHistoricalVolume = (candlesData: any[]): VolumeProcessingResult => {
  const volumes = candlesData.map((candle) => candle.volume || 0)
  const timestamps = candlesData.map((candle) => (candle.time as number) * 1000)

  return { volumes, timestamps }
}

/**
 * Procesa datos de volumen desde mensajes WebSocket
 */
export const processWebSocketVolume = (
  newVolume: number,
  currentVolumes: number[],
  currentTimestamps: number[],
  newTimestamp: number
): VolumeProcessingResult => {
  // Crear un mapa de volúmenes por timestamp para preservar datos previos
  const volumeByTime: Record<number, number> = {}

  for (let i = 0; i < currentTimestamps.length; i++) {
    const t = currentTimestamps[i]
    const v = currentVolumes[i] || 0
    if (Number.isFinite(t)) {
      volumeByTime[t] = v
    }
  }

  // Actualizar solo el último timestamp con el nuevo volumen
  volumeByTime[newTimestamp] = newVolume

  // Reconstruir arrays ordenados por timestamp
  const sortedTimestamps = Object.keys(volumeByTime)
    .map(Number)
    .sort((a, b) => a - b)

  const volumes = sortedTimestamps.map((t) => volumeByTime[t])

  return { volumes, timestamps: sortedTimestamps }
}

/**
 * Valida datos de volumen antes de usar
 */
export const validateVolumeData = (volumes: number[], timestamps: number[]): boolean => {
  if (!Array.isArray(volumes) || !Array.isArray(timestamps)) {
    return false
  }

  if (volumes.length !== timestamps.length) {
    return false
  }

  if (volumes.length === 0) {
    return false
  }

  // Verificar que todos los valores sean números válidos
  for (let i = 0; i < volumes.length; i++) {
    if (!Number.isFinite(volumes[i]) || !Number.isFinite(timestamps[i])) {
      return false
    }
  }

  return true
}

/**
 * Filtra datos de volumen para el chart con colores basados en dirección del precio
 */
export const filterVolumeDataForChart = (
  volumes: number[],
  timestamps: number[],
  candlesData?: any[]
) => {
  return volumes
    .map((value, index) => {
      // Determinar color basado en dirección del precio (si tenemos datos de velas)
      let color = '#9b59b6' // Color por defecto (morado)

      if (candlesData && candlesData[index]) {
        const candle = candlesData[index]
        // Verde si cerró arriba (bullish), rojo si cerró abajo (bearish)
        color = candle.close >= candle.open ? '#26a69a' : '#ef5350'
      }

      return {
        time: (timestamps[index] / 1000) as any,
        value,
        color
      }
    })
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
}
