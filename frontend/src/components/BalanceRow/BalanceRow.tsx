import React from 'react'
import './styles.css'
import type { BalanceRowProps } from './types'

const BalanceRow: React.FC<BalanceRowProps> = ({
  label,
  value,
  valueType = 'default',
  color,
  className = ''
}) => {
  const getValueClassName = () => {
    const baseClass = 'balance-value'
    const typeClass = valueType !== 'default' ? valueType : ''
    return `${baseClass} ${typeClass} ${className}`.trim()
  }

  const getValueStyle = () => {
    if (color) {
      return { color }
    }
    return {}
  }

  const getLabelStyle = () => {
    // Los labels heredan el mismo color que los valores
    if (color) {
      return { color }
    }

    // Colores específicos para tipos de valores
    switch (valueType) {
      case 'doge-rate':
        return { color: '#9c27b0' }
      default:
        return {}
    }
  }

  return (
    <div className="balance-row">
      <span className="balance-label" style={getLabelStyle()}>
        {label}
      </span>
      <span className={getValueClassName()} style={getValueStyle()}>
        {value}
      </span>
    </div>
  )
}

export default BalanceRow
