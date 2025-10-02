import type { ReactNode } from 'react'

export interface BalanceRowProps {
  label: string
  value: ReactNode
  valueType?: 'default' | 'pnl' | 'change' | 'status' | 'doge-rate' | 'current'
  color?: string
  className?: string
}
