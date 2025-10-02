#!/usr/bin/env python3
"""
Script para probar el sistema de saldo de cuenta
"""

from trading_tracker import TradingTracker
import time

def test_account_balance():
    """Prueba el sistema de saldo de cuenta"""
    
    print("🧪 Probando sistema de saldo de cuenta...")
    print("=" * 60)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Mostrar saldo inicial
    balance = tracker.get_account_balance()
    print(f"💰 Saldo inicial: ${balance['initial_balance']:.2f}")
    print(f"💰 Saldo actual: ${balance['current_balance']:.2f}")
    print(f"💰 PnL total: ${balance['total_pnl']:.2f}")
    print(f"💰 Cambio: {balance['balance_change_pct']:.2f}%")
    print()
    
    # Simular algunas operaciones
    test_operations = [
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9050},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.9050, 'exit_price': 0.8950},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8950, 'exit_price': 0.8800},
    ]
    
    for i, op in enumerate(test_operations):
        print(f"📊 Operación {i+1}: {op['bot']} {op['signal']}")
        
        # Abrir posición
        tracker.update_position(op['bot'], op['signal'], op['entry_price'], 100)
        time.sleep(0.1)
        
        # Cerrar posición
        tracker.update_position(op['bot'], 'HOLD', op['exit_price'], 100)
        
        # Mostrar saldo actualizado
        balance = tracker.get_account_balance()
        print(f"   💰 Saldo actual: ${balance['current_balance']:.2f}")
        print(f"   💰 PnL total: ${balance['total_pnl']:.2f}")
        print(f"   💰 Cambio: {balance['balance_change_pct']:.2f}%")
        print()
    
    # Mostrar resumen final
    balance = tracker.get_account_balance()
    print("=" * 60)
    print("📈 RESUMEN FINAL:")
    print(f"   Saldo inicial: ${balance['initial_balance']:.2f}")
    print(f"   Saldo final: ${balance['current_balance']:.2f}")
    print(f"   PnL total: ${balance['total_pnl']:.2f}")
    print(f"   Cambio porcentual: {balance['balance_change_pct']:.2f}%")
    print(f"   Estado: {'🟢 Rentable' if balance['is_profitable'] else '🔴 En Pérdida'}")
    
    print("\n✅ Prueba del sistema de saldo completada!")

if __name__ == "__main__":
    test_account_balance()
