import React, { useState } from 'react'
import './InfoBox.css'
import type { InfoBoxProps } from './types'

const InfoBox: React.FC<InfoBoxProps> = ({
  title,
  items,
  isActive = false,
  description,
  storageKey,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(() => {
    if (storageKey) {
      const saved = localStorage.getItem(storageKey)
      return saved ? JSON.parse(saved) : false
    }
    return false
  })

  const toggleExpansion = () => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)
    if (storageKey) {
      localStorage.setItem(storageKey, JSON.stringify(newExpanded))
    }
  }

  return (
    <div className={`info-box ${isActive ? 'active' : 'inactive'} ${className}`}>
      <div className="info-header" onClick={toggleExpansion}>
        {title} {isExpanded ? '▼' : '▶'}
      </div>

      {isExpanded && (
        <div className="info-content">
          {items.map((item, index) => (
            <div key={index} className="info-item">
              <span className="info-label">{item.label}:</span>
              <span className={`info-value ${item.className || ''}`}>{item.value}</span>
            </div>
          ))}

          {description && (
            <div className="info-description-section">
              <div className="info-label">Funcionamiento:</div>
              <div className="info-description-text">{description}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default InfoBox
