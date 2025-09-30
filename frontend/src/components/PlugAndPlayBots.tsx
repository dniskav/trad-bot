import { useApiBotActions, useApiBots, useApiProcessInfo } from '@hooks'
import React, { useEffect, useState } from 'react'
import { PluginBotCard, type BotInfo as PluginBotInfo } from './PluginBotCard'
import { ServerInfoAccordion } from './ServerInfoAccordion'

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
}

const PlugAndPlayBots: React.FC<PlugAndPlayBotsProps> = ({ className = '', currentPrice = 0 }) => {
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
  const { startBot, stopBot, updateBotConfig } = useApiBotActions()

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
      const botsData = await fetchBots()
      if (botsData) {
        // Filter out legacy bots (conservative, aggressive)
        const plugAndPlayBots = botsData.filter(
          (bot: any) => !['conservative', 'aggressive'].includes(bot.name)
        )

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

        //        console.log('🤖 PlugAndPlayBots: Setting new bots:', botsWithSynthetic)
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

  // WebSocket functionality removed - using only API data

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

      // Always update the backend configuration
      const configSuccess = await updateBotConfig(botName, { synthetic_mode: newSynthetic })
      if (!configSuccess) {
        console.error('Error updating bot configuration in backend')
        // Revert local state on error
        setBots((prev) => ({
          ...prev,
          [botName]: {
            ...prev[botName],
            synthetic_mode: currentSynthetic
          }
        }))
        saveSyntheticMode(botName, currentSynthetic)
        return
      }

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
        console.log(
          `💾 Saved synthetic mode for ${botName}: ${newSynthetic} (bot is inactive) - Backend updated`
        )
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
        <ServerInfoAccordion
          serverInfo={serverInfo}
          expanded={!!expandedBots['server']}
          onToggle={() => toggleBotExpansion('server')}
        />
      )}

      {/* Individual Bot Cards */}
      <div className="bots-list">
        {botEntries.map(([botName, botInfo]) => (
          <PluginBotCard
            key={botName}
            botName={botName}
            botInfo={botInfo as unknown as PluginBotInfo}
            botsLoading={botsLoading}
            onToggleBot={handleBotToggle}
            onToggleSynthetic={handleSyntheticToggle}
            getRiskLevelColor={getRiskLevelColor}
            getRiskLevelIcon={getRiskLevelIcon}
            getBotIcon={getBotIcon}
            formatUptime={formatUptime}
          />
        ))}
      </div>
    </div>
  )
}

export default PlugAndPlayBots
