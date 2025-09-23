import React from 'react'
import './ServerInfoAccordion.css'
import type { ServerInfoAccordionProps } from './types'

const ServerInfoAccordion: React.FC<ServerInfoAccordionProps> = ({
  serverInfo,
  expanded,
  onToggle
}) => {
  if (!serverInfo) return null

  return (
    <div className="server-info-accordion">
      <div className="accordion-header" onClick={onToggle}>
        <span className="accordion-title">🖥️ Información del Servidor</span>
        <span className="accordion-icon">{expanded ? '▼' : '▶'}</span>
      </div>
      {expanded && (
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
  )
}

export default ServerInfoAccordion
