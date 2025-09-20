import React, { useEffect, useState } from 'react'

interface AccordionProps {
  title: string
  icon?: string
  children: React.ReactNode
  defaultExpanded?: boolean
  className?: string
  storageKey?: string // New prop for localStorage key
}

const Accordion: React.FC<AccordionProps> = ({
  title,
  icon,
  children,
  defaultExpanded = false,
  className = '',
  storageKey
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
    setIsExpanded(!isExpanded)
  }

  return (
    <div className={`accordion ${className}`}>
      <div className="accordion-header" onClick={toggleExpanded}>
        <div className="accordion-title">
          {icon && <span className="accordion-icon">{icon}</span>}
          <span>{title}</span>
        </div>
        <div className="accordion-toggle">{isExpanded ? '▼' : '▶'}</div>
      </div>
      {isExpanded && <div className="accordion-content">{children}</div>}
    </div>
  )
}

export default Accordion
