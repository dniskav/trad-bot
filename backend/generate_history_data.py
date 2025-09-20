#!/usr/bin/env python3
"""
Script para generar datos de historial de posiciones para testing
"""

from trading_tracker import TradingTracker
import time
import random

def generate_history_data():
    """Genera datos de historial para testing"""
    
    print("🧪 Generando datos de historial de posiciones...")
    print("=" * 60)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Simular múltiples operaciones para generar historial
    test_scenarios = [
        # Bot Conservador - Operaciones exitosas
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9050, 'reason': 'Take Profit'},
        {'bot': 'conservative', 'signal': 'SELL', 'entry_price': 0.9050, 'exit_price': 0.8950, 'reason': 'Take Profit'},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8950, 'exit_price': 0.8800, 'reason': 'Stop Loss'},
        
        # Bot Agresivo - Operaciones mixtas
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.8800, 'exit_price': 0.8850, 'reason': 'Take Profit'},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.8850, 'exit_price': 0.8900, 'reason': 'Stop Loss'},
        {'bot': 'aggressive', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.8950, 'reason': 'Señal Contraria'},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.8950, 'exit_price': 0.8900, 'reason': 'Take Profit'},
        
        # Más operaciones para estadísticas
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9000, 'reason': 'Take Profit'},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.9000, 'exit_price': 0.8950, 'reason': 'Take Profit'},
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8950, 'exit_price': 0.8850, 'reason': 'Stop Loss'},
    ]
    
    for i, scenario in enumerate(test_scenarios):
        print(f"\n📊 Simulando operación {i+1}: {scenario['bot']} {scenario['signal']}")
        
        # Abrir posición
        tracker.update_position(scenario['bot'], scenario['signal'], scenario['entry_price'], 100)
        
        # Simular tiempo de espera
        time.sleep(0.1)
        
        # Cerrar posición con el precio de salida
        if scenario['reason'] == 'Take Profit':
            # Cambiar a HOLD para cerrar por take profit
            tracker.update_position(scenario['bot'], 'HOLD', scenario['exit_price'], 100)
        elif scenario['reason'] == 'Stop Loss':
            # Simular precio que activa stop loss
            tracker.update_position(scenario['bot'], scenario['signal'], scenario['exit_price'], 100)
        elif scenario['reason'] == 'Señal Contraria':
            # Cambiar señal para cerrar por señal contraria
            opposite_signal = 'SELL' if scenario['signal'] == 'BUY' else 'BUY'
            tracker.update_position(scenario['bot'], opposite_signal, scenario['exit_price'], 100)
    
    print("\n" + "=" * 60)
    print("📈 Estadísticas generadas:")
    
    # Mostrar estadísticas
    stats = tracker.get_bot_statistics()
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")
    print(f"   PnL total: ${stats['total_pnl_net']:.4f}")
    print(f"   Mejor trade: ${stats['best_trade']:.4f}")
    print(f"   Peor trade: ${stats['worst_trade']:.4f}")
    
    # Mostrar historial
    history = tracker.get_position_history(limit=10)
    print(f"\n📋 Últimas {len(history)} posiciones:")
    for pos in history[-5:]:  # Mostrar solo las últimas 5
        exit_price = pos.get('exit_price', pos.get('current_price', 0))
        print(f"   {pos['bot_type']} {pos['type']}: ${pos['entry_price']:.4f} → ${exit_price:.4f} | PnL: ${pos['pnl_net']:.4f} | {pos['close_reason']}")
    
    print("\n✅ Datos de historial generados exitosamente!")
    print("   El frontend ahora debería mostrar el historial completo.")

if __name__ == "__main__":
    generate_history_data()
