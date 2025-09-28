import { EventBusImpl } from './EventBusImpl'
import type { EventBus } from './types'

// Instancia global del event bus
export const eventBus: EventBus = new EventBusImpl()
