import type { EventBus } from './types'
import { EventType } from './types'

type EventCallback = (data: any) => void

class EventBusImpl implements EventBus {
  private events: Map<string, EventCallback[]> = new Map()
  private knownEvents: Set<string>

  constructor() {
    // Crear set de eventos conocidos
    this.knownEvents = new Set(Object.values(EventType))
  }

  on(event: string, callback: EventCallback): void {
    if (!this.events.has(event)) {
      this.events.set(event, [])
    }
    this.events.get(event)!.push(callback)
  }

  off(event: string, callback: EventCallback): void {
    const callbacks = this.events.get(event)
    if (callbacks) {
      const index = callbacks.indexOf(callback)
      if (index > -1) {
        callbacks.splice(index, 1)
      }
    }
  }

  emit(event: string, data: any): void {
    // Validar si el evento es conocido
    if (!this.knownEvents.has(event)) {
      console.warn(
        `⚠️ Evento no reconocido: "${event}". Eventos conocidos:`,
        Array.from(this.knownEvents)
      )
      return
    }

    const callbacks = this.events.get(event)
    if (callbacks) {
      callbacks.forEach((callback) => callback(data))
    }
  }

  // Método para agregar eventos personalizados (opcional)
  addKnownEvent(event: string): void {
    this.knownEvents.add(event)
  }

  // Método para obtener lista de eventos conocidos
  getKnownEvents(): string[] {
    return Array.from(this.knownEvents)
  }
}

export { EventBusImpl }
