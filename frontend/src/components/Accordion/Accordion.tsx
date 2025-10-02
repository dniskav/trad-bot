import React, { useEffect, useState } from 'react'
import './styles.css'
import type { AccordionProps } from './types'

const Accordion: React.FC<AccordionProps> = ({
  title,
  icon,
  children,
  defaultExpanded = false,
  className = '',
  storageKey,
  unmountOnCollapse = false,
  onExpand,
  onCollapse
}) => {
  // Generate a default storage key if none provided
  const key = storageKey || `accordion-${title.toLowerCase().replace(/\s+/g, '-')}`

  // Initialize state from localStorage or default
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window !== 'undefined' && storageKey) {
      const saved = localStorage.getItem(key)
      return saved !== null ? JSON.parse(saved) : defaultExpanded
    }
    return defaultExpanded
  })

  // Save to localStorage whenever state changes
  useEffect(() => {
    if (typeof window !== 'undefined' && storageKey) {
      localStorage.setItem(key, JSON.stringify(isExpanded))
    }
  }, [isExpanded, key, storageKey])

  const toggleExpanded = () => {
    const newExpanded = !isExpanded
    setIsExpanded(newExpanded)

    // Llamar callbacks opcionales
    if (newExpanded && onExpand) {
      onExpand()
    } else if (!newExpanded && onCollapse) {
      onCollapse()
    }
  }

  return (
    <div className={`accordion ${isExpanded ? 'expanded' : 'collapsed'} ${className}`}>
      <div className="accordion-header" onClick={toggleExpanded}>
        <div className="accordion-title">
          {icon && <span className="accordion-icon">{icon}</span>}
          <span>{title}</span>
        </div>
        <div className="accordion-toggle">{isExpanded ? '▲' : '▶'}</div>
      </div>
      {unmountOnCollapse ? (
        isExpanded ? (
          <div className="accordion-content">{children}</div>
        ) : null
      ) : (
        <div className="accordion-content" style={{ display: isExpanded ? 'block' : 'none' }}>
          {children}
        </div>
      )}
    </div>
  )
}

export default Accordion
