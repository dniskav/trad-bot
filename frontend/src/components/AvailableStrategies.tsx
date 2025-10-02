import API_CONFIG from '@config/api'
import { eventBus } from '@eventBus/eventBus'
import { EventType } from '@eventBus/types'
import apiClient from '@services/apiClient'
import React, { useEffect, useMemo, useState } from 'react'

const AvailableStrategies: React.FC = () => {
  const [available, setAvailable] = useState<string[]>([])
  const [loaded, setLoaded] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const fetchConfigs = async () => {
    setLoading(true)
    try {
      const res = await apiClient.get<string[]>(API_CONFIG.ENDPOINTS.STRATEGIES_CONFIGS)
      setAvailable(res.data || [])
      const loadedRes = await apiClient.get<{ strategies: { name: string }[] }>(
        API_CONFIG.ENDPOINTS.STRATEGIES_LOADED
      )
      setLoaded((loadedRes.data?.strategies || []).map((s) => s.name))
    } catch (e) {
      // noop
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchConfigs()
    const handler = () => fetchConfigs()
    eventBus.on(EventType.WS_SERVER_STRATEGIES, handler)
    return () => eventBus.off(EventType.WS_SERVER_STRATEGIES, handler)
  }, [])

  const load = async (name: string) => {
    try {
      await apiClient.post(API_CONFIG.ENDPOINTS.STRATEGY_LOAD(name))
    } catch (e) {}
  }

  const unload = async (name: string) => {
    try {
      await apiClient.post(API_CONFIG.ENDPOINTS.STRATEGY_UNLOAD(name))
    } catch (e) {}
  }

  const isLoaded = useMemo(() => new Set(loaded), [loaded])

  return (
    <div className="available-strategies">
      <h3 style={{ marginTop: 16 }}>📦 Estrategias disponibles</h3>
      {loading && <div>Cargando...</div>}
      <div className="list" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {available.map((name) => {
          const active = isLoaded.has(name)
          return (
            <button
              key={name}
              onClick={() => (active ? unload(name) : load(name))}
              style={{
                padding: '6px 10px',
                borderRadius: 8,
                border: '1px solid ' + (active ? '#2e7d32' : '#555'),
                background: active ? '#1b5e20' : 'transparent',
                color: active ? '#fff' : '#ccc',
                cursor: 'pointer'
              }}
              title={active ? 'Descargar' : 'Cargar'}>
              {name.toUpperCase()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default AvailableStrategies
