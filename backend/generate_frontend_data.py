#!/usr/bin/env python3
"""
Script para generar datos de historial y reiniciar el servidor
"""

from trading_tracker import TradingTracker
import time

def generate_history_and_restart():
    """Genera historial y reinicia el servidor"""
    
    print("🧪 Generando datos de historial para el servidor...")
    print("=" * 60)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Simular múltiples operaciones para generar historial
    test_scenarios = [
        # Bot Conservador - Operaciones exitosas
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9050},
        {'bot': 'conservative', 'signal': 'SELL', 'entry_price': 0.9050, 'exit_price': 0.8950},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8950, 'exit_price': 0.8800},
        
        # Bot Agresivo - Operaciones mixtas
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.8800, 'exit_price': 0.8850},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.8850, 'exit_price': 0.8900},
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.8950},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.8950, 'exit_price': 0.8900},
        
        # Más operaciones para estadísticas
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9000},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.9000, 'exit_price': 0.8950},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8950, 'exit_price': 0.8850},
    ]
    
    for i, scenario in enumerate(test_scenarios):
        print(f"📊 Simulando operación {i+1}: {scenario['bot']} {scenario['signal']}")
        
        # Abrir posición
        tracker.update_position(scenario['bot'], scenario['signal'], scenario['entry_price'], 100)
        time.sleep(0.1)
        
        # Cerrar posición
        tracker.update_position(scenario['bot'], 'HOLD', scenario['exit_price'], 100)
    
    print("\n" + "=" * 60)
    print("📈 Datos generados:")
    
    # Mostrar estadísticas
    stats = tracker.get_bot_statistics()
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")
    print(f"   PnL total: ${stats['total_pnl_net']:.4f}")
    
    # Mostrar saldo
    balance = tracker.get_account_balance()
    print(f"   Saldo inicial: ${balance['initial_balance']:.2f}")
    print(f"   Saldo actual: ${balance['current_balance']:.2f}")
    print(f"   Cambio: {balance['balance_change_pct']:.2f}%")
    
    # Mostrar historial
    history = tracker.get_position_history(limit=10)
    print(f"   Historial: {len(history)} posiciones")
    
    print("\n✅ Datos generados exitosamente!")
    print("   El servidor ahora debería mostrar el saldo y historial en el frontend.")
    print("   Revisa la consola del navegador para ver los logs de debug.")

if __name__ == "__main__":
    generate_history_and_restart()
