import React, { useContext, useEffect, useState } from 'react'
import { WebSocketContext } from '../contexts/WebSocketContext'
import { useApiBotActions, useApiBots, useApiProcessInfo } from '../hooks'
import InfoBox from './InfoBox'

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
  synthetic_balance_usdt: number
  bot_description: string
}

interface ServerInfo {
  memory_mb: number
  cpu_percent: number
  pid: number
  create_time: string
}

interface PlugAndPlayBotsProps {
  className?: string
  currentPrice?: number
  history?: any[]
  activePositions?: any
}

const PlugAndPlayBots: React.FC<PlugAndPlayBotsProps> = ({
  className = '',
  currentPrice = 0,
  history,
  activePositions
}) => {
  // console.log('🚀 PlugAndPlayBots: Component rendering') // Comentado para reducir spam

  const wsCtx = useContext(WebSocketContext)
  const [bots, setBots] = useState<Record<string, BotInfo>>({})
  const [expandedBots, setExpandedBots] = useState<Record<string, boolean>>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('plugin-bots-accordion')
      return saved ? JSON.parse(saved) : {}
    }
    return {}
  })
  const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null)

  // Use API hooks
  const { fetchBots, isLoading: botsLoading, error: botsError } = useApiBots()
  const { data: processInfoData } = useApiProcessInfo()
  const { startBot, stopBot } = useApiBotActions()

  // Debug: Log current price changes
  useEffect(() => {
    console.log('💰 PlugAndPlayBots: Current price updated:', currentPrice)
  }, [currentPrice])

  // Load synthetic mode from localStorage
  const loadSyntheticMode = (botName: string): boolean => {
    const stored = localStorage.getItem(`bot_${botName}_synthetic`)
    return stored ? JSON.parse(stored) : false
  }

  // Save synthetic mode to localStorage
  const saveSyntheticMode = (botName: string, synthetic: boolean) => {
    localStorage.setItem(`bot_${botName}_synthetic`, JSON.stringify(synthetic))
  }

  // Fetch bots data using the new hooks
  useEffect(() => {
    const fetchData = async () => {
      console.log('🤖 PlugAndPlayBots: Fetching bots data...')
      const botsData = await fetchBots()
      if (botsData) {
        console.log('🤖 PlugAndPlayBots: Processing bots data:', botsData)

        // Filter out legacy bots (conservative, aggressive)
        const plugAndPlayBots = botsData.filter(
          (bot: any) => !['conservative', 'aggressive'].includes(bot.name)
        )

        console.log('🤖 PlugAndPlayBots: Filtered plug-and-play bots:', plugAndPlayBots)

        // Convert array to object and add additional info
        const botsWithSynthetic = Object.fromEntries(
          plugAndPlayBots.map((bot: any) => [
            bot.name,
            {
              ...bot,
              synthetic_mode: loadSyntheticMode(bot.name),
              synthetic_balance_usdt: getSyntheticBalance(),
              bot_description: getBotDescription(bot.name),
              config: {
                symbol: 'DOGEUSDT',
                interval: '1m',
                risk_level: 'medium',
                max_positions: 3,
                position_size: 0.5,
                synthetic_mode: loadSyntheticMode(bot.name)
              }
            }
          ])
        )

        console.log('🤖 PlugAndPlayBots: Setting new bots:', botsWithSynthetic)
        setBots(botsWithSynthetic)
      }
    }
    fetchData()
  }, []) // Only run once on mount

  // Update process info when data changes
  useEffect(() => {
    if (processInfoData) {
      setServerInfo(processInfoData)
    }
  }, [processInfoData])

  // Overlay en vivo con datos de plugin_bots_realtime desde el contexto
  useEffect(() => {
    if (!wsCtx || !wsCtx.pluginBotsRealtime) return
    const rt = wsCtx.pluginBotsRealtime
    if (!rt || Object.keys(rt).length === 0) return

    console.log('🔄 PlugAndPlayBots: WebSocket data received:', rt)

    setBots((prev) => {
      const next: Record<string, BotInfo> = { ...prev }
      Object.entries(rt as Record<string, any>).forEach(([name, info]) => {
        if (!next[name]) return

        console.log(`🔄 PlugAndPlayBots: Updating bot ${name} with data:`, info)

        next[name] = {
          ...next[name],
          is_active: info.is_active ?? next[name].is_active,
          positions_count: info.positions_count ?? next[name].positions_count,
          last_signal: info.last_signal ?? next[name].last_signal,
          uptime_seconds: info.uptime ?? next[name].uptime_seconds,
          start_time: info.start_time ?? next[name].start_time,
          synthetic_mode: info.synthetic_mode ?? next[name].synthetic_mode,
          synthetic_balance: info.synthetic_balance ?? next[name].synthetic_balance,
          author: info.author ?? next[name].author
        }
      })
      return next
    })
  }, [wsCtx?.pluginBotsRealtime])

  // Listen to other WebSocket messages for bot updates
  useEffect(() => {
    if (!wsCtx || !wsCtx.lastMessage) return

    const data = wsCtx.lastMessage.message
    console.log('🔄 PlugAndPlayBots: WebSocket message received:', data)

    if (data.type === 'initial_data' || data.type === 'update') {
      if (data.data && data.data.bot_status) {
        console.log('🔄 PlugAndPlayBots: Bot status from WebSocket:', data.data.bot_status)

        setBots((prev) => {
          const next: Record<string, BotInfo> = { ...prev }
          Object.entries(data.data.bot_status).forEach(([name, status]: [string, any]) => {
            if (!next[name]) return

            console.log(`🔄 PlugAndPlayBots: Updating bot ${name} status:`, status)

            next[name] = {
              ...next[name],
              is_active: status.is_active ?? next[name].is_active,
              positions_count: status.positions_count ?? next[name].positions_count,
              last_signal: status.last_signal ?? next[name].last_signal,
              uptime_seconds: status.uptime ?? next[name].uptime_seconds,
              start_time: status.start_time ?? next[name].start_time,
              synthetic_mode: status.synthetic_mode ?? next[name].synthetic_mode,
              author: status.author ?? next[name].author
            }
          })
          return next
        })
      }
    }
  }, [wsCtx?.lastMessage])

  const handleBotToggle = async (botName: string, isActive: boolean) => {
    try {
      if (isActive) {
        const success = await stopBot(botName)
        if (success) {
          // Update local state
          setBots((prev) => ({
            ...prev,
            [botName]: {
              ...prev[botName],
              is_active: false
            }
          }))
        }
      } else {
        const syntheticMode = loadSyntheticMode(botName)
        const success = await startBot(botName, syntheticMode)
        if (success) {
          // Update local state
          setBots((prev) => ({
            ...prev,
            [botName]: {
              ...prev[botName],
              is_active: true
            }
          }))
        }
      }
    } catch (error) {
      console.error('Error toggling bot:', error)
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

      // If bot is active, restart it with new synthetic mode
      if (bots[botName]?.is_active) {
        console.log(`🔄 Restarting bot ${botName} with synthetic mode: ${newSynthetic}`)

        // Stop the bot first
        const stopSuccess = await stopBot(botName)
        if (stopSuccess) {
          // Wait a moment then start with new synthetic mode
          setTimeout(async () => {
            const startSuccess = await startBot(botName, newSynthetic)
            if (!startSuccess) {
              console.error('Error restarting bot with new synthetic mode')
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
          }, 1000)
        } else {
          console.error('Error stopping bot for synthetic mode change')
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
      } else {
        console.log(`💾 Saved synthetic mode for ${botName}: ${newSynthetic} (bot is inactive)`)
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
    if (botName.includes('conservative')) return '🛡️'
    if (botName.includes('aggressive')) return '⚡'
    return '🔧'
  }

  const getBotDescription = (botName: string) => {
    const descriptions: Record<string, string> = {
      rsibot:
        'Analiza el RSI (Relative Strength Index) para detectar condiciones de sobrecompra/sobreventa. Genera señales BUY cuando RSI < 30 y SELL cuando RSI > 70.',
      macdbot:
        'Utiliza el indicador MACD (Moving Average Convergence Divergence) para identificar cambios de tendencia. Señales basadas en cruces de líneas MACD y histograma.',
      simplebot:
        'Bot de tendencia simple que analiza cambios de precio en períodos cortos. Genera señales BUY/SELL basadas en movimientos significativos de precio.',
      conservative:
        'Bot conservador SMA Cross con filtros RSI y Volumen. Usa medias móviles de 8/21 períodos con validación de momentum y volumen.',
      aggressive:
        'Bot agresivo SMA Cross con filtros RSI y Volumen. Usa medias móviles de 5/13 períodos para señales más rápidas y sensibles.'
    }
    return descriptions[botName] || 'Bot de trading automatizado con estrategia personalizada.'
  }

  const getSyntheticBalance = () => {
    // Cada bot tiene 1000 USDT de saldo synthetic
    return 1000
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

  // Show loading state when bots are loading and no data yet
  if (botsLoading && Object.keys(bots).length === 0) {
    return (
      <div className={`plug-and-play-bots ${className}`}>
        <h3>🔌 Bots Plug-and-Play</h3>
        <div className="loading">Cargando bots...</div>
      </div>
    )
  }

  // Show error state if there's an error
  if (botsError) {
    return (
      <div className={`plug-and-play-bots ${className}`}>
        <h3>🔌 Bots Plug-and-Play</h3>
        <div className="error">❌ {botsError}</div>
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
            className={`plugin-bot-card ${botInfo.is_active ? 'active' : 'inactive'}`}>
            <div className="plugin-bot-card-header">
              <div className="plugin-bot-header-left">
                <div className="plugin-bot-title">
                  <span className="plugin-bot-icon">{getBotIcon(botName)}</span>
                  <span className="plugin-bot-name">{botName}</span>
                  <span className="plugin-bot-status">{botInfo.is_active ? '🟢' : '🔴'}</span>
                  {botInfo.synthetic_mode && <span className="synthetic-badge">🧪</span>}
                </div>
                <div className="plugin-bot-description">{botInfo.description}</div>
              </div>

              <div className="plugin-bot-header-right">
                <button
                  className={`plugin-synthetic-toggle ${
                    botInfo.synthetic_mode ? 'active' : 'inactive'
                  }`}
                  onClick={() => handleSyntheticToggle(botName, botInfo.synthetic_mode)}
                  title={botInfo.synthetic_mode ? 'Modo Synthetic' : 'Modo Real'}>
                  {botInfo.synthetic_mode ? '🧪' : '💰'}
                </button>
                <button
                  className={`plugin-bot-toggle ${botInfo.is_active ? 'active' : 'inactive'}`}
                  onClick={() => handleBotToggle(botName, botInfo.is_active)}
                  disabled={botsLoading}>
                  {botInfo.is_active ? 'OFF' : 'ON'}
                </button>
              </div>
            </div>

            <div className="plugin-bot-card-content">
              <div className="plugin-bot-metrics-row">
                <div className="plugin-metric">
                  <span className="plugin-metric-label">Posiciones:</span>
                  <span className="plugin-metric-value">{botInfo.positions_count}</span>
                </div>
                <div className="plugin-metric">
                  <span className="plugin-metric-label">Riesgo:</span>
                  <span
                    className="plugin-metric-value"
                    style={{ color: getRiskLevelColor(botInfo.config.risk_level) }}>
                    {getRiskLevelIcon(botInfo.config.risk_level)} {botInfo.config.risk_level}
                  </span>
                </div>
                <div className="plugin-metric">
                  <span className="plugin-metric-label">Tamaño:</span>
                  <span className="plugin-metric-value">${botInfo.config.position_size}</span>
                </div>
                <div className="plugin-metric">
                  <span className="plugin-metric-label">Símbolo:</span>
                  <span className="plugin-metric-value">{botInfo.config.symbol}</span>
                </div>
                <div className="plugin-metric">
                  <span className="plugin-metric-label">Precio:</span>
                  <span className="plugin-metric-value">${currentPrice.toFixed(5)}</span>
                </div>
                {botInfo.synthetic_mode && (
                  <div className="plugin-metric">
                    <span className="plugin-metric-label">Saldo Synthetic:</span>
                    <span className="plugin-metric-value">
                      ${botInfo.synthetic_balance_usdt} USDT
                    </span>
                  </div>
                )}
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

              <InfoBox
                title="📊 Info"
                isActive={botInfo.is_active}
                storageKey={`plugin-bot-${botName}-accordion`}
                description={botInfo.bot_description}
                items={[
                  {
                    label: 'Versión',
                    value: botInfo.version
                  },
                  {
                    label: 'Autor',
                    value: botInfo.author
                  },
                  {
                    label: 'Intervalo',
                    value: botInfo.config.interval
                  },
                  {
                    label: 'Max Posiciones',
                    value: botInfo.config.max_positions
                  },
                  {
                    label: 'Tamaño Posición',
                    value: `$${botInfo.config.position_size}`
                  },
                  {
                    label: 'Nivel Riesgo',
                    value: botInfo.config.risk_level
                  },
                  ...(botInfo.is_active
                    ? [
                        {
                          label: 'Tiempo Activo',
                          value: formatUptime(botInfo.uptime_seconds)
                        },
                        {
                          label: 'Iniciado',
                          value: botInfo.start_time
                            ? new Date(botInfo.start_time).toLocaleString()
                            : 'N/A'
                        },
                        {
                          label: 'Posiciones',
                          value: botInfo.positions_count
                        },
                        {
                          label: 'Modo',
                          value: botInfo.synthetic_mode ? 'Synthetic' : 'Real'
                        }
                      ]
                    : [])
                ]}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PlugAndPlayBots
