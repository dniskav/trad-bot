#!/usr/bin/env python3
"""
Script para probar órdenes reales con precisión corregida
"""

import logging
from real_trading_manager import real_trading_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_real_orders():
    """Prueba órdenes reales con diferentes cantidades"""
    
    logger.info("🧪 Iniciando prueba de órdenes reales...")
    
    # Verificar estado del trading
    status = real_trading_manager.get_trading_status()
    logger.info(f"📊 Estado del trading: {status['trading_enabled']}")
    logger.info(f"💰 Balance: {status['account_balance']}")
    
    if not real_trading_manager.is_trading_enabled():
        logger.error("❌ Trading no habilitado")
        return
    
    # Obtener precio actual de ADAUSDT
    current_price = real_trading_manager.get_current_price('ADAUSDT')
    if not current_price:
        logger.error("❌ No se pudo obtener el precio actual")
        return
    
    logger.info(f"📈 Precio actual de ADAUSDT: ${current_price}")
    
    # Probar orden conservadora
    logger.info("🤖 Probando bot conservador...")
    result_conservative = real_trading_manager.place_order('conservative', 'BUY', current_price)
    logger.info(f"Resultado conservador: {result_conservative}")
    
    # Probar orden agresiva
    logger.info("🤖 Probando bot agresivo...")
    result_aggressive = real_trading_manager.place_order('aggressive', 'BUY', current_price)
    logger.info(f"Resultado agresivo: {result_aggressive}")
    
    logger.info("✅ Prueba completada")

if __name__ == "__main__":
    test_real_orders()
