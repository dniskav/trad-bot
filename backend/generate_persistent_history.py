#!/usr/bin/env python3
"""
Script para generar datos de historial persistentes para el frontend
"""

from trading_tracker import TradingTracker
import time

def generate_persistent_history():
    """Genera datos de historial que se guardarán en JSON"""
    
    print("🧪 Generando datos de historial persistentes...")
    print("=" * 60)
    
    # Crear tracker (esto cargará datos existentes si los hay)
    tracker = TradingTracker()
    
    # Mostrar estado inicial
    balance = tracker.get_account_balance()
    history = tracker.get_position_history()
    stats = tracker.get_bot_statistics()
    
    print(f"📂 Estado inicial:")
    print(f"   Posiciones existentes: {len(history)}")
    print(f"   Saldo actual: ${balance['current_balance']:.2f}")
    print(f"   PnL total: ${balance['total_pnl']:.2f}")
    print()
    
    # Simular múltiples operaciones para generar historial completo
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
        
        # Operaciones adicionales para más historial
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.8850, 'exit_price': 0.8900},
        {'bot': 'conservative', 'signal': 'SELL', 'entry_price': 0.8900, 'exit_price': 0.8950},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.8950, 'exit_price': 0.8900},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9000},
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.9000, 'exit_price': 0.9050},
    ]
    
    print(f"📊 Simulando {len(test_scenarios)} operaciones...")
    
    for i, scenario in enumerate(test_scenarios):
        print(f"   Operación {i+1}: {scenario['bot']} {scenario['signal']}")
        
        # Abrir posición
        tracker.update_position(scenario['bot'], scenario['signal'], scenario['entry_price'], 100)
        time.sleep(0.05)  # Pequeña pausa
        
        # Cerrar posición
        tracker.update_position(scenario['bot'], 'HOLD', scenario['exit_price'], 100)
    
    print("\n" + "=" * 60)
    print("📈 DATOS GENERADOS:")
    
    # Mostrar estadísticas finales
    balance = tracker.get_account_balance()
    history = tracker.get_position_history()
    stats = tracker.get_bot_statistics()
    
    print(f"   Total posiciones: {len(history)}")
    print(f"   Saldo inicial: ${balance['initial_balance']:.2f}")
    print(f"   Saldo final: ${balance['current_balance']:.2f}")
    print(f"   PnL total: ${balance['total_pnl']:.2f}")
    print(f"   Cambio: {balance['balance_change_pct']:.2f}%")
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")
    print(f"   Mejor trade: ${stats['best_trade']:.4f}")
    print(f"   Peor trade: ${stats['worst_trade']:.4f}")
    
    print("\n✅ Datos persistentes generados exitosamente!")
    print("   El historial se guardó automáticamente en logs/trading_history.json")
    print("   Reinicia el servidor para ver los datos en el frontend.")
    print("   Los datos se cargarán automáticamente al inicio.")

if __name__ == "__main__":
    generate_persistent_history()
