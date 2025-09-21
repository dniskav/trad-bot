#!/usr/bin/env python3
"""
Script para probar orden real con cantidad exacta
"""

import logging
from real_trading_manager import real_trading_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_exact_order():
    """Prueba una orden con cantidad exacta"""
    
    logger.info("🧪 Probando orden con cantidad exacta...")
    
    # Obtener precio actual
    current_price = real_trading_manager.get_current_price('ADAUSDT')
    logger.info(f"📈 Precio actual: ${current_price}")
    
    # Calcular cantidad exacta para $6 (más que el mínimo de $5)
    target_usdt = 6.0
    quantity_ada = target_usdt / current_price
    
    # Ajustar según step size de ADA (0.1)
    quantity_ada = round(quantity_ada / 0.1) * 0.1
    quantity_ada = max(0.1, quantity_ada)  # Mínimo 0.1 ADA
    
    actual_usdt = quantity_ada * current_price
    
    logger.info(f"💰 Objetivo: ${target_usdt}")
    logger.info(f"📊 Cantidad ADA: {quantity_ada}")
    logger.info(f"💰 Valor real: ${actual_usdt:.2f}")
    
    # Probar orden directa
    logger.info("🚀 Ejecutando orden directa...")
    result = real_trading_manager.place_order_raw('ADAUSDT', 'BUY', quantity_ada)
    
    logger.info(f"✅ Resultado: {result}")
    
    if result['success']:
        logger.info("🎉 ¡Orden ejecutada exitosamente!")
        logger.info(f"   Order ID: {result['order']['orderId']}")
        logger.info(f"   Cantidad: {result['quantity']} ADA")
    else:
        logger.error(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    test_exact_order()
