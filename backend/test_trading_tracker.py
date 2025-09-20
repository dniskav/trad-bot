#!/usr/bin/env python3
"""
Script para probar el sistema de tracking de posiciones
"""

import time
import logging
from trading_tracker import trading_tracker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simulate_trading_scenario():
    """Simula un escenario de trading para probar el tracking"""
    
    logger.info("🎭 Iniciando simulación de trading...")
    
    # Escenario: Precio subiendo, bot detecta BUY
    prices = [0.90, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]
    signals = ['HOLD', 'HOLD', 'BUY', 'BUY', 'BUY', 'BUY', 'BUY', 'HOLD', 'HOLD', 'HOLD']
    
    logger.info("📈 Simulando precio subiendo...")
    
    for i, (price, signal) in enumerate(zip(prices, signals)):
        logger.info(f"\n--- Minuto {i+1} ---")
        logger.info(f"💰 Precio: ${price:.4f}")
        logger.info(f"📊 Señal: {signal}")
        
        # Actualizar posición conservadora
        trading_tracker.update_position('conservative', signal, price)
        
        # Mostrar estado actual
        position = trading_tracker.get_position_info('conservative')
        if position:
            logger.info(f"📊 Posición: {position['type']} a ${position['entry_price']:.4f}")
            logger.info(f"💵 PnL: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
        else:
            logger.info("📊 Sin posición abierta")
        
        time.sleep(1)  # Pausa para ver los cambios
    
    logger.info("\n🎯 Simulación completada!")
    
    # Mostrar resumen final
    all_positions = trading_tracker.get_all_positions()
    logger.info(f"📋 Estado final: {all_positions}")

if __name__ == "__main__":
    simulate_trading_scenario()
