#!/usr/bin/env python3
"""
Script para investigar los filtros de ADAUSDT en Binance
"""

import logging
from real_trading_manager import real_trading_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def investigate_ada_filters():
    """Investiga los filtros de ADAUSDT"""
    
    logger.info("🔍 Investigando filtros de ADAUSDT...")
    
    if not real_trading_manager.client:
        logger.error("❌ Cliente de Binance no inicializado")
        return
    
    try:
        # Obtener información del símbolo
        symbol_info = real_trading_manager.client.get_symbol_info('ADAUSDT')
        
        logger.info("📊 Información del símbolo ADAUSDT:")
        logger.info(f"   Símbolo: {symbol_info['symbol']}")
        logger.info(f"   Estado: {symbol_info['status']}")
        logger.info(f"   Base Asset: {symbol_info['baseAsset']}")
        logger.info(f"   Quote Asset: {symbol_info['quoteAsset']}")
        
        logger.info("\n🔧 Filtros:")
        for filter_info in symbol_info['filters']:
            filter_type = filter_info['filterType']
            logger.info(f"   {filter_type}: {filter_info}")
            
            if filter_type == 'LOT_SIZE':
                logger.info(f"     📏 Cantidad mínima: {filter_info['minQty']}")
                logger.info(f"     📏 Cantidad máxima: {filter_info['maxQty']}")
                logger.info(f"     📏 Step size: {filter_info['stepSize']}")
            
            elif filter_type == 'NOTIONAL':
                logger.info(f"     💰 Valor mínimo: {filter_info['minNotional']}")
                logger.info(f"     💰 Valor máximo: {filter_info['maxNotional']}")
            
            elif filter_type == 'PRICE_FILTER':
                logger.info(f"     💲 Precio mínimo: {filter_info['minPrice']}")
                logger.info(f"     💲 Precio máximo: {filter_info['maxPrice']}")
                logger.info(f"     💲 Tick size: {filter_info['tickSize']}")
        
        # Calcular cantidades válidas
        current_price = real_trading_manager.get_current_price('ADAUSDT')
        logger.info(f"\n💰 Precio actual: ${current_price}")
        
        # Encontrar filtros relevantes
        lot_size_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'), None)
        notional_filter = next((f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL'), None)
        
        if lot_size_filter and notional_filter:
            min_qty = float(lot_size_filter['minQty'])
            step_size = float(lot_size_filter['stepSize'])
            min_notional = float(notional_filter['minNotional'])
            
            # Calcular cantidad mínima válida
            min_quantity_for_notional = min_notional / current_price
            min_quantity_for_lot = min_qty
            
            # Ajustar según step size
            if step_size >= 1.0:
                min_quantity_for_notional = int(min_quantity_for_notional)
                min_quantity_for_lot = int(min_quantity_for_lot)
            else:
                decimals = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
                min_quantity_for_notional = round(min_quantity_for_notional, decimals)
                min_quantity_for_lot = round(min_quantity_for_lot, decimals)
            
            logger.info(f"\n📈 Cálculos:")
            logger.info(f"   Cantidad mínima por LOT_SIZE: {min_quantity_for_lot}")
            logger.info(f"   Cantidad mínima por NOTIONAL: {min_quantity_for_notional}")
            logger.info(f"   Cantidad mínima final: {max(min_quantity_for_lot, min_quantity_for_notional)}")
            
            # Probar con cantidad mínima válida
            test_quantity = max(min_quantity_for_lot, min_quantity_for_notional)
            test_notional = test_quantity * current_price
            
            logger.info(f"\n🧪 Prueba con cantidad mínima:")
            logger.info(f"   Cantidad: {test_quantity} ADA")
            logger.info(f"   Valor: ${test_notional:.2f}")
            logger.info(f"   ¿Cumple LOT_SIZE? {test_quantity >= min_qty}")
            logger.info(f"   ¿Cumple NOTIONAL? {test_notional >= min_notional}")
        
    except Exception as e:
        logger.error(f"❌ Error investigando filtros: {e}")

if __name__ == "__main__":
    investigate_ada_filters()
