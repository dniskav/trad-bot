#!/usr/bin/env python3
"""
Script simple para probar las señales de demostración
"""

import random
from trading_tracker import trading_tracker

def test_demo_signals():
    """Prueba las señales de demostración"""
    
    print("🎭 Probando señales de demostración...")
    print("=" * 50)
    
    # Función para generar señales de demostración
    def generate_demo_signals():
        signals = ['BUY', 'SELL', 'HOLD']
        weights = [0.3, 0.3, 0.4]  # 30% BUY, 30% SELL, 40% HOLD
        
        conservative = random.choices(signals, weights=weights)[0]
        aggressive = random.choices(signals, weights=weights)[0]
        
        return conservative, aggressive
    
    # Simular varios ciclos
    for i in range(10):
        print(f"\n--- Ciclo {i+1} ---")
        
        # Generar señales
        conservative_signal, aggressive_signal = generate_demo_signals()
        current_price = 0.90 + random.uniform(-0.02, 0.02)
        
        print(f"💰 Precio: ${current_price:.4f}")
        print(f"🐌 Conservador: {conservative_signal}")
        print(f"⚡ Agresivo: {aggressive_signal}")
        
        # Actualizar posiciones
        trading_tracker.update_position('conservative', conservative_signal, current_price)
        trading_tracker.update_position('aggressive', aggressive_signal, current_price)
        
        # Mostrar estado
        conservative_pos = trading_tracker.get_position_info('conservative')
        aggressive_pos = trading_tracker.get_position_info('aggressive')
        
        if conservative_pos:
            print(f"📊 Conservador - {conservative_pos['type']} a ${conservative_pos['entry_price']:.4f}")
            print(f"💵 PnL: ${conservative_pos['pnl']:.4f} ({conservative_pos['pnl_pct']:.2f}%)")
        
        if aggressive_pos:
            print(f"📊 Agresivo - {aggressive_pos['type']} a ${aggressive_pos['entry_price']:.4f}")
            print(f"💵 PnL: ${aggressive_pos['pnl']:.4f} ({aggressive_pos['pnl_pct']:.2f}%)")
        
        print("-" * 30)
    
    print("\n🎯 Prueba completada!")
    print("📋 Estado final:")
    all_positions = trading_tracker.get_all_positions()
    print(f"Conservador: {all_positions['conservative']}")
    print(f"Agresivo: {all_positions['aggressive']}")

if __name__ == "__main__":
    test_demo_signals()
