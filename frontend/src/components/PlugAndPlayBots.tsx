import React, { useEffect, useRef, useState } from 'react'

interface BotInfo {
  name: string
  description: string
  version: string
  author: string
  is_active: boolean
  positions_count: number
  last_signal: any
  synthetic_mode: boolean
  synthetic_balance: any
  start_time: string | null
  uptime_seconds: number | null
  uptime_formatted: string | null
  config: {
    symbol: string
    interval: string
    risk_level: string
    max_positions: number
    position_size: number
    synthetic_mode: boolean
  }
}

interface ServerInfo {
  memory_mb: number
  cpu_percent: number
  pid: number
  create_time: string
}

interface PlugAndPlayBotsProps {
  className?: string
}

const PlugAndPlayBots: React.FC<PlugAndPlayBotsProps> = ({ className = '' }) => {
  // console.log('🚀 PlugAndPlayBots: Component rendering') // Comentado para reducir spam

  const [bots, setBots] = useState<Record<string, BotInfo>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedBots, setExpandedBots] = useState<Record<string, boolean>>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('plugin-bots-accordion')
      return saved ? JSON.parse(saved) : {}
    }
    return {}
  })
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null)

  // Load synthetic mode from localStorage
  const loadSyntheticMode = (botName: string): boolean => {
    const stored = localStorage.getItem(`bot_${botName}_synthetic`)
    return stored ? JSON.parse(stored) : false
  }

  // Save synthetic mode to localStorage
  const saveSyntheticMode = (botName: string, synthetic: boolean) => {
    localStorage.setItem(`bot_${botName}_synthetic`, JSON.stringify(synthetic))
  }

  // Use ref to persist lastFetchTime across renders
  const lastFetchTimeRef = useRef(0)
  const MIN_FETCH_INTERVAL = 15000 // 15 seconds minimum between fetches

  // Fetch bots data with proper debouncing
  useEffect(() => {
    // console.log('🔄 PlugAndPlayBots: useEffect triggered') // Comentado para reducir spam
    let isMounted = true

    const fetchAllData = async () => {
      if (!isMounted) return

      const now = Date.now()
      if (now - lastFetchTimeRef.current < MIN_FETCH_INTERVAL) {
        // console.log('🚫 PlugAndPlayBots: Skipping fetch - too soon') // Comentado para reducir spam
        return
      }

      // console.log('🔄 PlugAndPlayBots: Fetching all data...') // Comentado para reducir spam
      lastFetchTimeRef.current = now

      try {
        setLoading(true)

        // Fetch both endpoints in parallel
        const [botsResponse, serverResponse] = await Promise.all([
          fetch('/api/bots'),
          fetch('/bot/process-info')
        ])

        if (!isMounted) return

        const [botsResult, serverResult] = await Promise.all([
          botsResponse.json(),
          serverResponse.json()
        ])

        if (!isMounted) return

        // Process bots data
        if (botsResult.status === 'success') {
          // Filter out legacy bots (conservative, aggressive)
          const plugAndPlayBots = Object.fromEntries(
            Object.entries(botsResult.data.bots).filter(
              ([name]) => !['conservative', 'aggressive'].includes(name)
            )
          )

          // console.log('🔍 PlugAndPlayBots: Filtered bots:', Object.keys(plugAndPlayBots)) // Comentado para reducir spam

          // Apply synthetic mode from localStorage
          const botsWithSynthetic = Object.fromEntries(
            Object.entries(plugAndPlayBots).map(([name, bot]) => [
              name,
              {
                ...bot,
                synthetic_mode: loadSyntheticMode(name)
              }
            ])
          )

          setBots(botsWithSynthetic)
          setError(null)
          // console.log(
          //   '✅ PlugAndPlayBots: Bots data updated successfully, count:',
          //   Object.keys(botsWithSynthetic).length
          // ) // Comentado para reducir spam
        } else {
          setError('Error al cargar bots')
          console.error('❌ PlugAndPlayBots: Error response:', botsResult)
        }

        // Process server info
        if (serverResult.status === 'success' && isMounted) {
          setServerInfo(serverResult.data)
          // console.log('✅ PlugAndPlayBots: Server info updated successfully') // Comentado para reducir spam
        } else {
          console.warn(
            '⚠️ PlugAndPlayBots: Server info not available, continuing with bots data only'
          )
        }
      } catch (err) {
        if (!isMounted) return
        setError('Error de conexión')
        console.error('❌ PlugAndPlayBots: Fetch error:', err)
      } finally {
        if (isMounted) {
          setLoading(false)
          // console.log('🔄 PlugAndPlayBots: Loading state set to false') // Comentado para reducir spam
        }
      }
    }

    // Initial fetch
    // console.log('🚀 PlugAndPlayBots: Component mounted, starting initial fetch') // Comentado para reducir spam
    fetchAllData()

    // Poll every 30 seconds (increased interval to reduce load)
    const interval = setInterval(() => {
      if (isMounted) {
        // console.log('⏰ PlugAndPlayBots: Interval tick - fetching data') // Comentado para reducir spam
        fetchAllData()
      }
    }, 30000)

    return () => {
      // console.log('🛑 PlugAndPlayBots: Component unmounting, cleaning up') // Comentado para reducir spam
      isMounted = false
      clearInterval(interval)
    }
  }, []) // Empty dependency array since AppSetup handles the timing

  const handleBotToggle = async (botName: string, isActive: boolean) => {
    try {
      const action = isActive ? 'stop' : 'start'
      const response = await fetch(`/api/bots/${botName}/${action}`, {
        method: 'POST'
      })
      const result = await response.json()

      if (result.status === 'success') {
        // Update local state
        setBots((prev) => ({
          ...prev,
          [botName]: {
            ...prev[botName],
            is_active: !isActive
          }
        }))
      } else {
        console.error('Error toggling bot:', result.message)
      }
    } catch (err) {
      console.error('Error toggling bot:', err)
    }
  }

  const handleSyntheticToggle = async (botName: string, currentSynthetic: boolean) => {
    try {
      const newSynthetic = !currentSynthetic

      // Save to localStorage
      saveSyntheticMode(botName, newSynthetic)

      // Update local state
      setBots((prev) => ({
        ...prev,
        [botName]: {
          ...prev[botName],
          synthetic_mode: newSynthetic
        }
      }))

      // Send to backend
      const response = await fetch(`/api/bots/${botName}/synthetic`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          synthetic_mode: newSynthetic
        })
      })

      const result = await response.json()
      if (result.status !== 'success') {
        console.error('Error toggling synthetic mode:', result.message)
        // Revert local state on error
        setBots((prev) => ({
          ...prev,
          [botName]: {
            ...prev[botName],
            synthetic_mode: currentSynthetic
          }
        }))
        saveSyntheticMode(botName, currentSynthetic)
      }
    } catch (err) {
      console.error('Error toggling synthetic mode:', err)
      // Revert local state on error
      setBots((prev) => ({
        ...prev,
        [botName]: {
          ...prev[botName],
          synthetic_mode: currentSynthetic
        }
      }))
      saveSyntheticMode(botName, currentSynthetic)
    }
  }

  const toggleBotExpansion = (botName: string) => {
    setExpandedBots((prev) => {
      const newState = {
        ...prev,
        [botName]: !prev[botName]
      }
      // Save to localStorage
      if (typeof window !== 'undefined') {
        localStorage.setItem('plugin-bots-accordion', JSON.stringify(newState))
      }
      return newState
    })
  }

  const getRiskLevelColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low':
        return '#26a69a'
      case 'medium':
        return '#ffa726'
      case 'high':
        return '#ef5350'
      default:
        return '#666'
    }
  }

  const getRiskLevelIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low':
        return '🟢'
      case 'medium':
        return '🟡'
      case 'high':
        return '🔴'
      default:
        return '⚪'
    }
  }

  const getBotIcon = (botName: string) => {
    if (botName.includes('rsi')) return '📊'
    if (botName.includes('macd')) return '📈'
    if (botName.includes('simple')) return '🤖'
    return '🔧'
  }

  const formatUptime = (uptimeSeconds: number | null) => {
    if (!uptimeSeconds) return 'N/A'

    const hours = Math.floor(uptimeSeconds / 3600)
    const minutes = Math.floor((uptimeSeconds % 3600) / 60)
    const seconds = uptimeSeconds % 60

    if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`
    } else if (minutes > 0) {
      return `${minutes}m ${seconds}s`
    } else {
      return `${seconds}s`
    }
  }

  if (loading) {
    // console.log(
    //   '🔄 PlugAndPlayBots: Rendering loading state, bots count:',
    //   Object.keys(bots).length
    // ) // Comentado para reducir spam
    return (
      <div className={`plug-and-play-bots ${className}`}>
        <h3>🔌 Bots Plug-and-Play</h3>
        <div className="loading">Cargando bots...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`plug-and-play-bots ${className}`}>
        <h3>🔌 Bots Plug-and-Play</h3>
        <div className="error">❌ {error}</div>
      </div>
    )
  }

  const botEntries = Object.entries(bots)

  // console.log(
  //   '🔍 PlugAndPlayBots: Current state - loading:',
  //   loading,
  //   'bots count:',
  //   botEntries.length,
  //   'error:',
  //   error
  // ) // Comentado para reducir spam

  if (botEntries.length === 0) {
    return (
      <div className={`plug-and-play-bots ${className}`}>
        <h3>🔌 Bots Plug-and-Play</h3>
        <div className="no-bots">No hay bots plug-and-play disponibles</div>
      </div>
    )
  }

  return (
    <div className={`plug-and-play-bots ${className}`}>
      <h3>🔌 Bots Plug-and-Play ({botEntries.length})</h3>

      {/* Server Info Accordion */}
      {serverInfo && (
        <div className="server-info-accordion">
          <div className="accordion-header" onClick={() => toggleBotExpansion('server')}>
            <span className="accordion-title">🖥️ Información del Servidor</span>
            <span className="accordion-icon">{expandedBots['server'] ? '▼' : '▶'}</span>
          </div>
          {expandedBots['server'] && (
            <div className="accordion-content">
              <div className="server-metrics">
                <div className="server-metric">
                  <span className="metric-label">PID:</span>
                  <span className="metric-value">{serverInfo.pid}</span>
                </div>
                <div className="server-metric">
                  <span className="metric-label">Memoria:</span>
                  <span className="metric-value">{serverInfo.memory_mb} MB</span>
                </div>
                <div className="server-metric">
                  <span className="metric-label">CPU:</span>
                  <span className="metric-value">{serverInfo.cpu_percent}%</span>
                </div>
                <div className="server-metric">
                  <span className="metric-label">Iniciado:</span>
                  <span className="metric-value">
                    {new Date(serverInfo.create_time).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Individual Bot Cards */}
      <div className="bots-list">
        {botEntries.map(([botName, botInfo]) => (
          <div
            key={botName}
            className={`bot-card-full ${botInfo.is_active ? 'active' : 'inactive'}`}>
            <div className="bot-card-header">
              <div className="bot-main-info">
                <div className="bot-title">
                  <span className="bot-icon">{getBotIcon(botName)}</span>
                  <span className="bot-name">{botName}</span>
                  <span className="bot-status">{botInfo.is_active ? '🟢' : '🔴'}</span>
                  {botInfo.synthetic_mode && <span className="synthetic-badge">🧪</span>}
                </div>
                <div className="bot-description">{botInfo.description}</div>
              </div>

              <div className="bot-controls">
                <button
                  className={`synthetic-toggle ${botInfo.synthetic_mode ? 'active' : 'inactive'}`}
                  onClick={() => handleSyntheticToggle(botName, botInfo.synthetic_mode)}
                  title={botInfo.synthetic_mode ? 'Modo Synthetic' : 'Modo Real'}>
                  {botInfo.synthetic_mode ? '🧪 Synthetic' : '💰 Real'}
                </button>
                <button
                  className={`bot-toggle ${botInfo.is_active ? 'active' : 'inactive'}`}
                  onClick={() => handleBotToggle(botName, botInfo.is_active)}
                  disabled={loading}>
                  {botInfo.is_active ? '⏹️ Detener' : '▶️ Iniciar'}
                </button>
              </div>
            </div>

            <div className="bot-metrics-row">
              <div className="metric">
                <span className="metric-label">Posiciones:</span>
                <span className="metric-value">{botInfo.positions_count}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Riesgo:</span>
                <span
                  className="metric-value"
                  style={{ color: getRiskLevelColor(botInfo.config.risk_level) }}>
                  {getRiskLevelIcon(botInfo.config.risk_level)} {botInfo.config.risk_level}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Tamaño:</span>
                <span className="metric-value">${botInfo.config.position_size}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Símbolo:</span>
                <span className="metric-value">{botInfo.config.symbol}</span>
              </div>
            </div>

            {botInfo.last_signal && (
              <div className="bot-signal">
                <div className="signal-header">
                  <span className="signal-label">Última Señal:</span>
                  <span
                    className="signal-value"
                    style={{
                      color:
                        botInfo.last_signal.signal_type === 'BUY'
                          ? '#26a69a'
                          : botInfo.last_signal.signal_type === 'SELL'
                          ? '#ef5350'
                          : '#ffa726'
                    }}>
                    {botInfo.last_signal.signal_type}
                  </span>
                </div>
                <div className="signal-reasoning">{botInfo.last_signal.reasoning}</div>
                <div className="signal-confidence">
                  Confianza: {(botInfo.last_signal.confidence * 100).toFixed(1)}%
                </div>
              </div>
            )}

            <div className="bot-accordion">
              <div className="accordion-header" onClick={() => toggleBotExpansion(botName)}>
                <span className="accordion-title">📊 Detalles del Bot</span>
                <span className="accordion-icon">{expandedBots[botName] ? '▼' : '▶'}</span>
              </div>

              {expandedBots[botName] && (
                <div className="accordion-content">
                  <div className="bot-details">
                    <div className="detail-section">
                      <h4>📋 Configuración</h4>
                      <div className="detail-grid">
                        <div className="detail-item">
                          <span className="detail-label">Versión:</span>
                          <span className="detail-value">{botInfo.version}</span>
                        </div>
                        <div className="detail-item">
                          <span className="detail-label">Autor:</span>
                          <span className="detail-value">{botInfo.author}</span>
                        </div>
                        <div className="detail-item">
                          <span className="detail-label">Intervalo:</span>
                          <span className="detail-value">{botInfo.config.interval}</span>
                        </div>
                        <div className="detail-item">
                          <span className="detail-label">Max Posiciones:</span>
                          <span className="detail-value">{botInfo.config.max_positions}</span>
                        </div>
                      </div>
                    </div>

                    {botInfo.is_active && (
                      <div className="detail-section">
                        <h4>⏱️ Estado del Bot</h4>
                        <div className="detail-grid">
                          <div className="detail-item">
                            <span className="detail-label">Tiempo Activo:</span>
                            <span className="detail-value">
                              {formatUptime(botInfo.uptime_seconds)}
                            </span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Iniciado:</span>
                            <span className="detail-value">
                              {botInfo.start_time
                                ? new Date(botInfo.start_time).toLocaleString()
                                : 'N/A'}
                            </span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Posiciones Abiertas:</span>
                            <span className="detail-value">{botInfo.positions_count}</span>
                          </div>
                          <div className="detail-item">
                            <span className="detail-label">Modo:</span>
                            <span className="detail-value">
                              {botInfo.synthetic_mode ? '🧪 Synthetic' : '💰 Real'}
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                    {botInfo.last_signal?.metadata && (
                      <div className="detail-section">
                        <h4>📊 Métricas Técnicas</h4>
                        <div className="detail-grid">
                          {Object.entries(botInfo.last_signal.metadata).map(([key, value]) => (
                            <div key={key} className="detail-item">
                              <span className="detail-label">{key}:</span>
                              <span className="detail-value">
                                {typeof value === 'number' ? value.toFixed(4) : String(value)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PlugAndPlayBots
