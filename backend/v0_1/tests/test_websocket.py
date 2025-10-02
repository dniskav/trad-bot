#!/usr/bin/env python3
"""
Script para probar la conexión WebSocket del Trading Bot
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    """Prueba la conexión WebSocket y muestra los datos recibidos"""
    
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"🔌 Conectando a {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Conexión WebSocket establecida!")
            print("📡 Esperando datos en tiempo real...")
            print("-" * 50)
            
            # Recibir mensajes por 30 segundos
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Esperar mensaje con timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    # Parsear el mensaje JSON
                    data = json.loads(message)
                    
                    # Mostrar información según el tipo de mensaje
                    if data.get("type") == "connection":
                        print(f"🔗 {data['type'].upper()}: {data['data']['status']}")
                        print(f"   Timestamp: {data['data']['timestamp']}")
                        
                    elif data.get("type") == "price":
                        price_data = data['data']
                        print(f"💰 {data['type'].upper()}:")
                        print(f"   Precio: ${price_data.get('price', 'N/A')}")
                        print(f"   Señal: {price_data.get('signal', 'N/A')}")
                        print(f"   Velas: {len(price_data.get('candles', []))} datos")
                        print(f"   Timestamp: {price_data.get('timestamp', 'N/A')}")
                        
                        # Mostrar última vela si hay datos
                        candles = price_data.get('candles', [])
                        if candles:
                            last_candle = candles[-1]
                            print(f"   Última vela: O:{last_candle['open']} H:{last_candle['high']} L:{last_candle['low']} C:{last_candle['close']}")
                    
                    print("-" * 50)
                    
                    # Verificar si han pasado 30 segundos
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        print(f"⏰ Timeout de {timeout} segundos alcanzado. Cerrando conexión...")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏳ Timeout esperando mensaje...")
                    continue
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"   Mensaje recibido: {message}")
                except Exception as e:
                    print(f"❌ Error procesando mensaje: {e}")
                    break
                    
    except ConnectionRefusedError:
        print("❌ Error: No se pudo conectar al WebSocket")
        print("   Asegúrate de que el servidor esté corriendo en http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False
    
    print("👋 Conexión WebSocket cerrada")
    return True

if __name__ == "__main__":
    print("🚀 Probando WebSocket del Trading Bot")
    print("=" * 50)
    
    # Ejecutar el test
    success = asyncio.run(test_websocket())
    
    if success:
        print("✅ Test completado exitosamente")
    else:
        print("❌ Test falló")
        sys.exit(1) 