export interface InfoItem {
  label: string
  value: string | number
  className?: string
}

export interface InfoBoxProps {
  title: string
  items: InfoItem[]
  isActive?: boolean
  description?: string
  storageKey?: string
  className?: string
}
