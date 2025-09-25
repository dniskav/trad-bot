import type { ReactNode } from 'react'

export interface AccordionProps {
  title: string
  icon?: string
  children: ReactNode
  defaultExpanded?: boolean
  className?: string
  storageKey?: string
  unmountOnCollapse?: boolean
  onExpand?: () => void
  onCollapse?: () => void
}
