#!/usr/bin/env python3
"""
Script para probar las señales del bot
"""

import os
import time
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from sma_cross_bot import generate_signal as conservative_signal, get_closes, SYMBOL, INTERVAL
from aggressive_scalping_bot import generate_signal as aggressive_signal

# Configuración
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

def test_bot_signals():
    """Prueba las señales de ambos bots"""
    print("🤖 Probando señales del bot...")
    print("=" * 50)
    
    try:
        # Obtener datos
        closes = get_closes(SYMBOL, INTERVAL, limit=100)
        current_price = closes[-1]
        
        # Generar señales
        conservative_sig = conservative_signal(closes)
        aggressive_sig = aggressive_signal(closes)
        
        print(f"💰 Precio Actual: ${current_price:.2f}")
        print(f"🐌 Bot Conservador: {conservative_sig}")
        print(f"⚡ Bot Agresivo: {aggressive_sig}")
        
        # Calcular fuerza de señales
        import numpy as np
        
        # Conservador: SMA 5 vs 20
        sma_fast_cons = np.mean(closes[-5:])
        sma_slow_cons = np.mean(closes[-20:])
        strength_cons = (sma_fast_cons - sma_slow_cons) / sma_slow_cons if sma_slow_cons != 0 else 0
        
        # Agresivo: SMA 3 vs 8
        sma_fast_agg = np.mean(closes[-3:])
        sma_slow_agg = np.mean(closes[-8:])
        strength_agg = (sma_fast_agg - sma_slow_agg) / sma_slow_agg if sma_slow_agg != 0 else 0
        
        print(f"📊 Fuerza Conservador: {strength_cons:.4f}")
        print(f"📊 Fuerza Agresivo: {strength_agg:.4f}")
        
        print("=" * 50)
        
        # Simular datos que enviaría el WebSocket
        bot_signals = {
            "conservative": conservative_sig,
            "aggressive": aggressive_sig,
            "current_price": current_price
        }
        
        print("📡 Datos que se envían al frontend:")
        print(f"bot_signals: {bot_signals}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_bot_signals()
