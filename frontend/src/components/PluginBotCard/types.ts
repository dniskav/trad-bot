export type RiskLevel = 'low' | 'medium' | 'high' | string

export interface BotConfig {
  symbol: string
  interval: string
  risk_level: RiskLevel
  max_positions: number
  position_size: number
  synthetic_mode: boolean
}

export interface BotInfo {
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
  config: BotConfig
  synthetic_balance_usdt: number
  bot_description: string
}

export interface PluginBotCardProps {
  botName: string
  botInfo: BotInfo
  botsLoading: boolean
  onToggleBot: (botName: string, isActive: boolean) => void
  onToggleSynthetic: (botName: string, currentSynthetic: boolean) => void
  getRiskLevelColor: (riskLevel: RiskLevel) => string
  getRiskLevelIcon: (riskLevel: RiskLevel) => string
  getBotIcon: (botName: string) => string
  formatUptime: (uptimeSeconds: number | null) => string
}
