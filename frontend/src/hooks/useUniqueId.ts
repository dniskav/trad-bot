import { useMemo } from 'react'

/**
 * Hook para generar IDs únicos para elementos de formulario
 * Evita problemas de accesibilidad con IDs duplicados
 */
export const useUniqueId = (prefix: string = 'element'): string => {
  return useMemo(() => `${prefix}-${Math.random().toString(36).substr(2, 9)}`, [prefix])
}

