#!/usr/bin/env python3
"""
Bot de demostración que genera señales artificiales para mostrar el sistema
"""

import time
import random
from datetime import datetime
from trading_tracker import trading_tracker

def generate_demo_signals():
    """Genera señales de demostración para mostrar el sistema"""
    
    print("🎭 Iniciando bot de demostración...")
    print("📊 Generando señales artificiales cada 30 segundos...")
    print("=" * 60)
    
    # Simular precio base
    base_price = 0.90
    current_price = base_price
    
    # Señales posibles
    signals = ['BUY', 'SELL', 'HOLD']
    
    for i in range(20):  # 20 iteraciones = 10 minutos
        print(f"\n--- Iteración {i+1} ---")
        print(f"⏰ Tiempo: {datetime.now().strftime('%H:%M:%S')}")
        
        # Generar señal aleatoria (más probabilidad de BUY/SELL que HOLD)
        signal_weights = [0.4, 0.4, 0.2]  # 40% BUY, 40% SELL, 20% HOLD
        conservative_signal = random.choices(signals, weights=signal_weights)[0]
        aggressive_signal = random.choices(signals, weights=signal_weights)[0]
        
        # Simular movimiento de precio
        price_change = random.uniform(-0.01, 0.01)  # ±1%
        current_price += price_change
        current_price = max(0.85, min(0.95, current_price))  # Mantener en rango
        
        print(f"💰 Precio: ${current_price:.4f}")
        print(f"🐌 Conservador: {conservative_signal}")
        print(f"⚡ Agresivo: {aggressive_signal}")
        
        # Actualizar posiciones
        trading_tracker.update_position('conservative', conservative_signal, current_price)
        trading_tracker.update_position('aggressive', aggressive_signal, current_price)
        
        # Mostrar estado de posiciones
        conservative_pos = trading_tracker.get_position_info('conservative')
        aggressive_pos = trading_tracker.get_position_info('aggressive')
        
        if conservative_pos:
            print(f"📊 Conservador - {conservative_pos['type']} a ${conservative_pos['entry_price']:.4f}")
            print(f"💵 PnL: ${conservative_pos['pnl']:.4f} ({conservative_pos['pnl_pct']:.2f}%)")
        
        if aggressive_pos:
            print(f"📊 Agresivo - {aggressive_pos['type']} a ${aggressive_pos['entry_price']:.4f}")
            print(f"💵 PnL: ${aggressive_pos['pnl']:.4f} ({aggressive_pos['pnl_pct']:.2f}%)")
        
        print("-" * 40)
        
        # Esperar 30 segundos
        time.sleep(30)
    
    print("\n🎯 Demostración completada!")
    print("📋 Estado final de posiciones:")
    all_positions = trading_tracker.get_all_positions()
    print(f"Conservador: {all_positions['conservative']}")
    print(f"Agresivo: {all_positions['aggressive']}")

if __name__ == "__main__":
    generate_demo_signals()
