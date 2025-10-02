#!/usr/bin/env python3
"""
Script para probar la persistencia JSON del historial
"""

from trading_tracker import TradingTracker
import time
import os

def test_json_persistence():
    """Prueba el sistema de persistencia JSON"""
    
    print("🧪 Probando persistencia JSON del historial...")
    print("=" * 60)
    
    # Verificar si existe archivo previo
    history_file = "logs/trading_history.json"
    backup_file = "logs/trading_history_backup.json"
    
    print(f"📁 Archivo de historial: {history_file}")
    print(f"📁 Archivo de backup: {backup_file}")
    print(f"📁 Existe historial: {os.path.exists(history_file)}")
    print(f"📁 Existe backup: {os.path.exists(backup_file)}")
    print()
    
    # Crear tracker (esto debería cargar datos existentes)
    print("🔄 Creando tracker (cargando datos existentes)...")
    tracker = TradingTracker()
    
    # Mostrar estado inicial
    balance = tracker.get_account_balance()
    history = tracker.get_position_history()
    stats = tracker.get_bot_statistics()
    
    print(f"📂 Posiciones cargadas: {len(history)}")
    print(f"💰 Saldo inicial: ${balance['initial_balance']:.2f}")
    print(f"💰 Saldo actual: ${balance['current_balance']:.2f}")
    print(f"💰 PnL total: ${balance['total_pnl']:.2f}")
    print(f"📊 Total trades: {stats['total_trades']}")
    print()
    
    # Simular algunas operaciones nuevas
    print("📊 Simulando operaciones nuevas...")
    test_operations = [
        {'bot': 'conservative', 'signal': 'BUY', 'entry_price': 0.8900, 'exit_price': 0.9050},
        {'bot': 'aggressive', 'signal': 'SELL', 'entry_price': 0.9050, 'exit_price': 0.8950},
    ]
    
    for i, op in enumerate(test_operations):
        print(f"   Operación {i+1}: {op['bot']} {op['signal']}")
        
        # Abrir posición
        tracker.update_position(op['bot'], op['signal'], op['entry_price'], 100)
        time.sleep(0.1)
        
        # Cerrar posición
        tracker.update_position(op['bot'], 'HOLD', op['exit_price'], 100)
    
    # Mostrar estado final
    balance = tracker.get_account_balance()
    history = tracker.get_position_history()
    stats = tracker.get_bot_statistics()
    
    print("\n" + "=" * 60)
    print("📈 ESTADO FINAL:")
    print(f"   Posiciones totales: {len(history)}")
    print(f"   Saldo actual: ${balance['current_balance']:.2f}")
    print(f"   PnL total: ${balance['total_pnl']:.2f}")
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Win rate: {stats['win_rate']:.1f}%")
    
    # Verificar que se crearon los archivos
    print("\n" + "=" * 60)
    print("📁 VERIFICACIÓN DE ARCHIVOS:")
    print(f"   Historial existe: {os.path.exists(history_file)}")
    print(f"   Backup existe: {os.path.exists(backup_file)}")
    
    if os.path.exists(history_file):
        file_size = os.path.getsize(history_file)
        print(f"   Tamaño del archivo: {file_size} bytes")
    
    print("\n✅ Prueba de persistencia completada!")
    print("   Los datos se guardaron automáticamente en JSON.")
    print("   Reinicia el servidor para verificar que se cargan correctamente.")

if __name__ == "__main__":
    test_json_persistence()
