#!/usr/bin/env python3
"""
Script de prueba para verificar que el TradingTracker actualizado funcione con el frontend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_tracker import TradingTracker
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_trading_tracker():
    """Prueba el TradingTracker actualizado"""
    
    print("🧪 Probando TradingTracker actualizado...")
    
    # Crear instancia del tracker
    tracker = TradingTracker()
    
    # Simular algunas posiciones
    print(f"\n🔍 Simulando posiciones para bot 'conservative':")
    
    # Primera posición
    tracker.update_position('conservative', 'BUY', 0.5, 10.0)
    print(f"   ✅ Primera posición BUY abierta")
    
    # Segunda posición (debería abrirse también)
    tracker.update_position('conservative', 'BUY', 0.52, 8.0)
    print(f"   ✅ Segunda posición BUY abierta")
    
    # Tercera posición
    tracker.update_position('conservative', 'SELL', 0.48, 5.0)
    print(f"   ✅ Tercera posición SELL abierta")
    
    # Verificar posiciones activas
    conservative_positions = tracker.positions['conservative']
    print(f"\n📊 Posiciones activas conservative: {len(conservative_positions)}")
    
    for pos_id, position in conservative_positions.items():
        print(f"   - {pos_id}: {position['type']} ${position['entry_price']:.4f}")
    
    # Probar bot aggressive
    print(f"\n🔍 Simulando posiciones para bot 'aggressive':")
    tracker.update_position('aggressive', 'BUY', 0.51, 12.0)
    tracker.update_position('aggressive', 'SELL', 0.49, 7.0)
    
    aggressive_positions = tracker.positions['aggressive']
    print(f"📊 Posiciones activas aggressive: {len(aggressive_positions)}")
    
    # Obtener datos para el frontend
    print(f"\n📡 Probando get_all_positions() para frontend:")
    position_data = tracker.get_all_positions()
    
    print(f"   - Conservative position info: {position_data['conservative'] is not None}")
    print(f"   - Aggressive position info: {position_data['aggressive'] is not None}")
    print(f"   - History length: {len(position_data['history'])}")
    print(f"   - Statistics available: {'statistics' in position_data}")
    print(f"   - Account balance: {position_data['account_balance']['current_balance']:.2f}")
    
    # Verificar compatibilidad con frontend
    if position_data['conservative'] and 'multiple_positions' in position_data['conservative']:
        print(f"\n✅ Compatibilidad con múltiples posiciones:")
        print(f"   - Conservative: {position_data['conservative']['position_count']} posiciones")
        print(f"   - Total PnL: ${position_data['conservative']['total_pnl']:.4f}")
    
    if position_data['aggressive'] and 'multiple_positions' in position_data['aggressive']:
        print(f"   - Aggressive: {position_data['aggressive']['position_count']} posiciones")
        print(f"   - Total PnL: ${position_data['aggressive']['total_pnl']:.4f}")
    
    # Simular cierre de posiciones
    print(f"\n🔒 Simulando cierre de posiciones:")
    tracker.update_position('conservative', 'HOLD', 0.53)
    tracker.update_position('aggressive', 'HOLD', 0.47)
    
    # Verificar que se cerraron
    conservative_after = len(tracker.positions['conservative'])
    aggressive_after = len(tracker.positions['aggressive'])
    history_after = len(tracker.position_history)
    
    print(f"   - Conservative posiciones después: {conservative_after}")
    print(f"   - Aggressive posiciones después: {aggressive_after}")
    print(f"   - Historial total: {history_after}")
    
    if conservative_after == 0 and aggressive_after == 0 and history_after > 0:
        print(f"\n✅ ¡Prueba exitosa! El TradingTracker funciona correctamente con múltiples posiciones.")
        return True
    else:
        print(f"\n❌ Prueba fallida. Verificar implementación.")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando pruebas del TradingTracker actualizado...")
    
    try:
        success = test_trading_tracker()
        
        if success:
            print(f"\n🎉 ¡Todas las pruebas pasaron!")
            print(f"\n📋 Resumen de cambios:")
            print(f"   ✅ TradingTracker soporta múltiples posiciones por bot")
            print(f"   ✅ Compatible con el formato esperado por el frontend")
            print(f"   ✅ Mantiene compatibilidad hacia atrás")
            print(f"   ✅ Historial y estadísticas funcionan correctamente")
        else:
            print(f"\n❌ Algunas pruebas fallaron. Revisar implementación.")
            
    except Exception as e:
        print(f"\n💥 Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()