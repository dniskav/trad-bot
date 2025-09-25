import React from 'react'
import { InfoBox } from '../InfoBox'
import BotSignal from './BotSignal'
import './PluginBotCard.css'
import type { PluginBotCardProps } from './types'

const PluginBotCard: React.FC<PluginBotCardProps> = ({
  botName,
  botInfo,
  botsLoading,
  onToggleBot,
  onToggleSynthetic,
  getRiskLevelColor,
  getRiskLevelIcon,
  getBotIcon,
  formatUptime
}) => {
  return (
    <div key={botName} className={`plugin-bot-card ${botInfo.is_active ? 'active' : 'inactive'}`}>
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
            className={`plugin-synthetic-toggle ${botInfo.synthetic_mode ? 'active' : 'inactive'}`}
            onClick={() => onToggleSynthetic(botName, botInfo.synthetic_mode)}
            title={botInfo.synthetic_mode ? 'Modo Synthetic' : 'Modo Real'}>
            {botInfo.synthetic_mode ? '🧪' : '💰'}
          </button>
          <button
            className={`plugin-bot-toggle ${botInfo.is_active ? 'active' : 'inactive'}`}
            onClick={() => onToggleBot(botName, botInfo.is_active)}
            disabled={botsLoading}>
            {botInfo.is_active ? 'OFF' : 'ON'}
          </button>
        </div>
      </div>

      <div className="plugin-bot-card-content">
        <div className="plugin-bot-metrics-row">
          <div className="plugin-metric">
            <span className="plugin-metric-label">Saldo:</span>
            <span className="plugin-metric-value">
              {botInfo.synthetic_mode
                ? `$${
                    (botInfo as any).synthetic_balance ??
                    (botInfo as any).synthetic_balance_usdt ??
                    0
                  } USDT`
                : botInfo.positions_count}
            </span>
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
        </div>

        {botInfo.last_signal && <BotSignal signal={botInfo.last_signal} />}

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
  )
}

export default PluginBotCard
