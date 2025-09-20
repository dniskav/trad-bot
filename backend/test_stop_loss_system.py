#!/usr/bin/env python3
"""
Script para probar el sistema de stop loss y take profit
"""

from trading_tracker import TradingTracker
import time

def test_stop_loss_system():
    """Prueba el sistema de stop loss y take profit"""
    
    print("🧪 Probando sistema de Stop Loss y Take Profit...")
    print("=" * 60)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Simular operación BUY con bot conservador
    print("📊 Simulando operación BUY con Bot Conservador:")
    print("   Precio de entrada: $0.8900")
    print("   Stop Loss: 1.5% (${:.4f})".format(0.8900 * 0.985))
    print("   Take Profit: 2.0% (${:.4f})".format(0.8900 * 1.020))
    print()
    
    # Abrir posición BUY
    tracker.update_position('conservative', 'BUY', 0.8900, 100)
    position = tracker.get_position_info('conservative')
    
    print("🚀 Posición abierta:")
    print(f"   Tipo: {position['type']}")
    print(f"   Precio entrada: ${position['entry_price']:.4f}")
    print(f"   Stop Loss: ${position['stop_loss']:.4f}")
    print(f"   Take Profit: ${position['take_profit']:.4f}")
    print()
    
    # Simular precio bajando hacia stop loss
    print("📉 Precio bajando hacia Stop Loss...")
    test_prices = [0.8880, 0.8860, 0.8840, 0.8820, 0.8800, 0.8780]
    
    for price in test_prices:
        tracker.update_position('conservative', 'BUY', price, 100)
        position = tracker.get_position_info('conservative')
        
        if position is None:
            print(f"🔒 Posición cerrada por Stop Loss a ${price:.4f}")
            break
        else:
            print(f"💰 Precio: ${price:.4f} | PnL: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
    
    print("\n" + "=" * 60)
    
    # Simular operación SELL con bot agresivo
    print("📊 Simulando operación SELL con Bot Agresivo:")
    print("   Precio de entrada: $0.9200")
    print("   Stop Loss: 0.8% (${:.4f})".format(0.9200 * 1.008))
    print("   Take Profit: 1.2% (${:.4f})".format(0.9200 * 0.988))
    print()
    
    # Abrir posición SELL
    tracker.update_position('aggressive', 'SELL', 0.9200, 100)
    position = tracker.get_position_info('aggressive')
    
    print("🚀 Posición abierta:")
    print(f"   Tipo: {position['type']}")
    print(f"   Precio entrada: ${position['entry_price']:.4f}")
    print(f"   Stop Loss: ${position['stop_loss']:.4f}")
    print(f"   Take Profit: ${position['take_profit']:.4f}")
    print()
    
    # Simular precio subiendo hacia take profit
    print("📈 Precio subiendo hacia Take Profit...")
    test_prices = [0.9180, 0.9160, 0.9140, 0.9120, 0.9100, 0.9080]
    
    for price in test_prices:
        tracker.update_position('aggressive', 'SELL', price, 100)
        position = tracker.get_position_info('aggressive')
        
        if position is None:
            print(f"🎯 Posición cerrada por Take Profit a ${price:.4f}")
            break
        else:
            print(f"💰 Precio: ${price:.4f} | PnL: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
    
    print("\n" + "=" * 60)
    print("✅ Pruebas completadas!")
    print("\n📋 Resumen de Stop Loss implementados:")
    print("   • Bot Conservador: 1.5% SL, 2.0% TP")
    print("   • Bot Agresivo: 0.8% SL, 1.2% TP")
    print("   • Bot Demo: 1.0% SL, 1.5% TP")
    print("   • Protección automática contra pérdidas grandes")
    print("   • Visualización en tiempo real en el frontend")

if __name__ == "__main__":
    test_stop_loss_system()
