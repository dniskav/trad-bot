export interface ServerInfo {
  memory_mb: number
  cpu_percent: number
  pid: number
  create_time: string
}

export interface ServerInfoAccordionProps {
  serverInfo: ServerInfo | null
  expanded: boolean
  onToggle: () => void
}
