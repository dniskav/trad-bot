#!/usr/bin/env python3
"""
Script para debuggear los datos que envía el servidor
"""

from trading_tracker import TradingTracker
import json

def debug_server_data():
    """Debug de los datos que envía el servidor"""
    
    print("🔍 Debuggeando datos del servidor...")
    print("=" * 60)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Simular algunas operaciones para generar datos
    print("📊 Simulando operaciones...")
    tracker.update_position('conservative', 'BUY', 0.8900, 100)
    tracker.update_position('conservative', 'HOLD', 0.9050, 100)  # Cerrar
    
    tracker.update_position('aggressive', 'SELL', 0.9050, 100)
    tracker.update_position('aggressive', 'HOLD', 0.8950, 100)  # Cerrar
    
    print("\n📋 Datos que envía get_all_positions():")
    print("=" * 60)
    
    all_positions = tracker.get_all_positions()
    
    # Mostrar estructura completa
    print("🔍 Estructura completa:")
    print(json.dumps(all_positions, indent=2, default=str))
    
    print("\n" + "=" * 60)
    print("🔍 Verificando campos específicos:")
    
    # Verificar cada campo
    print(f"✅ conservative position: {all_positions.get('conservative')}")
    print(f"✅ aggressive position: {all_positions.get('aggressive')}")
    print(f"✅ last_signals: {all_positions.get('last_signals')}")
    print(f"✅ history: {len(all_positions.get('history', []))} items")
    print(f"✅ statistics: {all_positions.get('statistics')}")
    print(f"✅ account_balance: {all_positions.get('account_balance')}")
    
    print("\n" + "=" * 60)
    print("🔍 Datos de account_balance:")
    if all_positions.get('account_balance'):
        balance = all_positions['account_balance']
        print(f"   initial_balance: {balance.get('initial_balance')}")
        print(f"   current_balance: {balance.get('current_balance')}")
        print(f"   total_pnl: {balance.get('total_pnl')}")
        print(f"   balance_change_pct: {balance.get('balance_change_pct')}")
        print(f"   is_profitable: {balance.get('is_profitable')}")
    
    print("\n" + "=" * 60)
    print("🔍 Datos de statistics:")
    if all_positions.get('statistics'):
        stats = all_positions['statistics']
        print(f"   conservative: {stats.get('conservative')}")
        print(f"   aggressive: {stats.get('aggressive')}")
        print(f"   overall: {stats.get('overall')}")
    
    print("\n✅ Debug completado!")

if __name__ == "__main__":
    debug_server_data()
