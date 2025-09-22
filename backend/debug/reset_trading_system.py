#!/usr/bin/env python3
"""
Script para resetear el sistema de trading con $10 USD
"""

from trading_tracker import TradingTracker
import json
import os

def reset_trading_system():
    """Resetea el sistema de trading con balance inicial de $10 USD"""
    
    print("🧹 Reseteando sistema de trading...")
    print("=" * 50)
    
    # Crear nuevo tracker con balance inicial de $10
    tracker = TradingTracker()
    
    # Configurar balance inicial
    tracker.initial_balance = 10.0
    tracker.current_balance = 10.0
    tracker.total_pnl = 0.0
    
    # Limpiar historial
    tracker.position_history = []
    tracker.last_signals = {
        'conservative': 'HOLD',
        'aggressive': 'HOLD'
    }
    
    # Guardar configuración inicial
    tracker.save_history()
    
    print(f"✅ Balance inicial configurado: ${tracker.initial_balance}")
    print(f"✅ Balance actual: ${tracker.current_balance}")
    print(f"✅ PnL total: ${tracker.total_pnl}")
    print(f"✅ Historial limpiado: {len(tracker.position_history)} posiciones")
    print()
    
    # Verificar que se guardó correctamente
    if os.path.exists("logs/trading_history.json"):
        print("✅ Archivo de historial creado correctamente")
        
        # Mostrar contenido del archivo
        with open("logs/trading_history.json", "r") as f:
            data = json.load(f)
            print(f"📊 Datos guardados:")
            print(f"   - Balance inicial: ${data.get('initial_balance', 0)}")
            print(f"   - Balance actual: ${data.get('current_balance', 0)}")
            print(f"   - PnL total: ${data.get('total_pnl', 0)}")
            print(f"   - Posiciones en historial: {len(data.get('position_history', []))}")
    else:
        print("❌ Error: No se pudo crear el archivo de historial")
    
    print("\n" + "=" * 50)
    print("🎯 SISTEMA RESETEADO PARA $10 USD")
    print("   • Balance inicial: $10.00")
    print("   • Historial limpio")
    print("   • Listo para trading real")

if __name__ == "__main__":
    reset_trading_system()
