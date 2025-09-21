#!/usr/bin/env python3
"""
Paquete de bots de trading plug-and-play
"""

from .rsi_bot import RSIBot, create_rsi_bot
from .macd_bot import MACDBot, create_macd_bot

__all__ = [
    'RSIBot',
    'create_rsi_bot',
    'MACDBot', 
    'create_macd_bot'
]
