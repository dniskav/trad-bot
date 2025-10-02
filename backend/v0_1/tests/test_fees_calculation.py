#!/usr/bin/env python3
"""
Script para probar el cálculo de comisiones de Binance
"""

from trading_tracker import TradingTracker
import time

def test_fees_calculation():
    """Prueba el cálculo de comisiones"""
    
    print("🧪 Probando cálculo de comisiones de Binance...")
    print("=" * 50)
    
    # Crear tracker
    tracker = TradingTracker()
    
    # Simular una operación completa
    print("📊 Simulando operación BUY:")
    print("   Precio de entrada: $0.8900")
    print("   Cantidad: 100 ADA")
    print("   Comisión por trade: 0.075% (con BNB)")
    print("   Comisión total: 0.15% (compra + venta)")
    print()
    
    # Abrir posición BUY
    tracker.update_position('conservative', 'BUY', 0.8900, 100)
    position = tracker.get_position_info('conservative')
    
    print("🚀 Posición abierta:")
    print(f"   Tipo: {position['type']}")
    print(f"   Precio entrada: ${position['entry_price']:.4f}")
    print(f"   Cantidad: {position['quantity']}")
    print(f"   Comisión entrada: ${position['entry_fee']:.4f}")
    print()
    
    # Simular cambio de precio
    print("📈 Precio sube a $0.9200 (+3.37%)")
    tracker.update_position('conservative', 'BUY', 0.9200, 100)
    position = tracker.get_position_info('conservative')
    
    print("💰 PnL actual:")
    print(f"   PnL Bruto: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
    print(f"   PnL Neto: ${position['pnl_net']:.4f} ({position['pnl_net_pct']:.2f}%)")
    print()
    
    # Cerrar posición
    print("🔒 Cerrando posición...")
    tracker.update_position('conservative', 'HOLD', 0.9200, 100)
    
    print("\n" + "=" * 50)
    print("✅ Prueba completada!")
    print("\n📋 Resumen de comisiones:")
    print("   • Comisión por trade: 0.075%")
    print("   • Total por operación: 0.15%")
    print("   • Impacto en rentabilidad: Significativo en trades pequeños")
    print("   • Recomendación: Usar BNB para pagar comisiones (-25% descuento)")

if __name__ == "__main__":
    test_fees_calculation()
