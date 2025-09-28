import React from 'react'
import './styles.css'
import type { AppSetupProps } from './types'

const AppSetup: React.FC<AppSetupProps> = ({ children }) => {
  // Mostrar la aplicación directamente
  return <>{children}</>
}

export default AppSetup
