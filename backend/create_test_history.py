#!/usr/bin/env python3
"""
Script para generar historial de posiciones de prueba
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_tracker import TradingTracker
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_history():
    """Crea un historial de posiciones de prueba"""
    
    print("🧪 Creando historial de posiciones de prueba...")
    
    # Crear instancia del tracker
    tracker = TradingTracker()
    
    # Simular algunas operaciones para generar historial
    print("\n📊 Simulando operaciones para bot 'conservative':")
    
    # Primera operación: BUY
    tracker.update_position('conservative', 'BUY', 0.50, 10.0)
    print("   ✅ Posición BUY abierta a $0.50")
    
    # Cerrar posición después de un tiempo
    tracker.update_position('conservative', 'HOLD', 0.52)
    print("   ✅ Posición cerrada a $0.52 (ganancia)")
    
    # Segunda operación: SELL
    tracker.update_position('conservative', 'SELL', 0.51, 8.0)
    print("   ✅ Posición SELL abierta a $0.51")
    
    # Cerrar posición
    tracker.update_position('conservative', 'HOLD', 0.49)
    print("   ✅ Posición cerrada a $0.49 (ganancia)")
    
    print("\n📊 Simulando operaciones para bot 'aggressive':")
    
    # Primera operación: BUY
    tracker.update_position('aggressive', 'BUY', 0.48, 12.0)
    print("   ✅ Posición BUY abierta a $0.48")
    
    # Cerrar posición
    tracker.update_position('aggressive', 'HOLD', 0.46)
    print("   ✅ Posición cerrada a $0.46 (pérdida)")
    
    # Segunda operación: SELL
    tracker.update_position('aggressive', 'SELL', 0.47, 6.0)
    print("   ✅ Posición SELL abierta a $0.47")
    
    # Cerrar posición
    tracker.update_position('aggressive', 'HOLD', 0.45)
    print("   ✅ Posición cerrada a $0.45 (ganancia)")
    
    # Verificar historial creado
    history = tracker.get_position_history()
    print(f"\n📋 Historial creado: {len(history)} posiciones")
    
    for i, pos in enumerate(history, 1):
        bot_type = pos.get('bot_type', 'unknown')
        pnl = pos.get('pnl_net', 0)
        print(f"   {i}. {bot_type.upper()}: ${pnl:.4f}")
    
    # Guardar historial
    tracker.save_history()
    print(f"\n💾 Historial guardado en logs/trading_history.json")
    
    # Verificar que se guardó correctamente
    import json
    with open('logs/trading_history.json', 'r') as f:
        data = json.load(f)
        print(f"📊 Verificación: {len(data['history'])} posiciones en archivo")
    
    return True

if __name__ == "__main__":
    print("🚀 Generando historial de posiciones de prueba...")
    
    try:
        success = create_test_history()
        
        if success:
            print(f"\n🎉 ¡Historial de prueba creado exitosamente!")
            print(f"\n📋 Ahora puedes:")
            print(f"   1. Reiniciar el servidor: python3 server_simple.py")
            print(f"   2. Abrir el frontend en http://localhost:3000")
            print(f"   3. Ver el historial de posiciones en la interfaz")
        else:
            print(f"\n❌ Error creando historial de prueba.")
            
    except Exception as e:
        print(f"\n💥 Error durante la creación: {e}")
        import traceback
        traceback.print_exc()
