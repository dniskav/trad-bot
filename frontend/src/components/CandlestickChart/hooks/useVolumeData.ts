import { useCallback, useState } from 'react'

export interface VolumeData {
  volume: number[]
  timestamps: number[]
  volumeType: 'quote' | 'base'
}

export interface UseVolumeDataReturn {
  volumeData: VolumeData | null
  setVolumeData: (data: VolumeData | null) => void
  updateVolumeData: (volumes: number[], timestamps: number[]) => void
  clearVolumeData: () => void
  setVolumeType: (type: 'quote' | 'base') => void
}

export const useVolumeData = (): UseVolumeDataReturn => {
  const [volumeData, setVolumeData] = useState<VolumeData | null>(null)

  const updateVolumeData = useCallback((volumes: number[], timestamps: number[]) => {
    setVolumeData((prev) => ({
      volume: volumes,
      timestamps: timestamps,
      volumeType: prev?.volumeType || 'quote'
    }))
  }, [])

  const clearVolumeData = useCallback(() => {
    setVolumeData(null)
  }, [])

  const setVolumeType = useCallback((type: 'quote' | 'base') => {
    setVolumeData((prev) => (prev ? { ...prev, volumeType: type } : null))
  }, [])

  return {
    volumeData,
    setVolumeData,
    updateVolumeData,
    clearVolumeData,
    setVolumeType
  }
}
