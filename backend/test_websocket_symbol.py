#!/usr/bin/env python3
"""
Script para verificar que el WebSocket esté enviando el símbolo correcto
"""

import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_symbol():
    """Prueba el WebSocket para verificar que envíe el símbolo correcto"""
    uri = "ws://localhost:8000/ws?interval=1m"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("🔌 Conectado al WebSocket")
            
            # Esperar mensajes
            for i in range(3):  # Solo 3 mensajes para la prueba
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(message)
                    
                    logger.info(f"📨 Mensaje {i+1}:")
                    logger.info(f"   Tipo: {data.get('type')}")
                    
                    if data.get('type') == 'candles' and data.get('data'):
                        symbol = data['data'].get('symbol')
                        logger.info(f"   Símbolo: {symbol}")
                        
                        if data['data'].get('bot_signals'):
                            bot_signals = data['data']['bot_signals']
                            logger.info(f"   Bot Signals: {bot_signals}")
                    
                    logger.info("-" * 40)
                    
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout esperando mensaje")
                    break
                    
    except Exception as e:
        logger.error(f"❌ Error conectando al WebSocket: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_symbol())
