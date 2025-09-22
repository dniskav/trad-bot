#!/usr/bin/env python3
"""
Logger personalizado con colores para resaltar trades y eventos importantes
"""

import logging
import sys
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Formatter que agrega colores a los logs según el tipo de mensaje"""
    
    # Códigos de color ANSI
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
        'BRIGHT_YELLOW': '\033[93m',
        'BRIGHT_GREEN': '\033[92m',
        'BRIGHT_RED': '\033[91m',
        'BRIGHT_BLUE': '\033[94m',
        'BRIGHT_MAGENTA': '\033[95m',
        'BRIGHT_CYAN': '\033[96m'
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
    
    def format(self, record):
        # Obtener el mensaje original
        original_message = record.getMessage()
        
        # Determinar el color basado en el contenido del mensaje
        color = self._get_color_for_message(original_message)
        
        # Aplicar el color al mensaje
        if color:
            colored_message = f"{color}{original_message}{self.COLORS['RESET']}"
            record.msg = colored_message
            record.args = ()
        
        return super().format(record)
    
    def _get_color_for_message(self, message: str) -> str:
        """Determina el color apropiado para el mensaje"""
        message_lower = message.lower()
        
        # Trades y posiciones REALES - AMARILLO BRILLANTE (solo acciones en tiempo real)
        if any(keyword in message_lower for keyword in [
            '🚀', 'nueva posición', 'nueva posicion', 'abriendo posición', 'abriendo posicion',
            '🔒', 'cerrando posición', 'cerrando posicion', 'posición cerrada', 'posicion cerrada',
            'trade ejecutado', 'trade exitoso', 'orden ejecutada', 'orden de margen ejecutada',
            'posición registrada', 'posicion registrada', 'cerrando posición por', 'cerrando posicion por'
        ]):
            return self.COLORS['BRIGHT_YELLOW']
        
        # Señales de trading - CYAN BRILLANTE
        if any(keyword in message_lower for keyword in [
            'señal', 'senal', 'signal', 'conservative', 'aggressive', 'bot'
        ]):
            return self.COLORS['BRIGHT_CYAN']
        
        # Errores - ROJO BRILLANTE
        if any(keyword in message_lower for keyword in [
            'error', '❌', 'failed', 'falló', 'fallo', 'exception'
        ]):
            return self.COLORS['BRIGHT_RED']
        
        # Advertencias - MAGENTA BRILLANTE
        if any(keyword in message_lower for keyword in [
            'warning', '⚠️', 'advertencia', 'cuidado', 'atención', 'atencion'
        ]):
            return self.COLORS['BRIGHT_MAGENTA']
        
        # Éxito y confirmaciones - VERDE BRILLANTE
        if any(keyword in message_lower for keyword in [
            '✅', 'éxito', 'exito', 'success', 'completado', 'sincronizado', 'conectado'
        ]):
            return self.COLORS['BRIGHT_GREEN']
        
        # Información de balance y dinero - AZUL BRILLANTE
        if any(keyword in message_lower for keyword in [
            '💰', 'balance', 'dinero', 'money', 'usdt', 'doge', 'capital'
        ]):
            return self.COLORS['BRIGHT_BLUE']
        
        # Mensajes históricos y de estado - SIN COLOR (gris normal)
        if any(keyword in message_lower for keyword in [
            'último trade', 'ultimo trade', 'historial guardado', 'posiciones activas',
            'sincronizado', 'actualizado desde', 'cargado desde', 'estado de bots'
        ]):
            return None  # Sin color para mensajes de estado/históricos
        
        # Por defecto, sin color
        return None

def setup_colored_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Configura un logger con colores"""
    
    # Crear el logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicar handlers
    if logger.handlers:
        return logger
    
    # Crear handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Crear formatter con colores
    formatter = ColoredFormatter(
        fmt='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Logger global con colores
colored_logger = setup_colored_logger('trading_bot_colored')

def get_colored_logger(name: str = None) -> logging.Logger:
    """Obtiene un logger con colores"""
    if name:
        return setup_colored_logger(name)
    return colored_logger
