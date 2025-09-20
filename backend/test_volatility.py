#!/usr/bin/env python3
"""
Script para probar diferentes símbolos y encontrar el más volátil
"""

import os
import time
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from sma_cross_bot import generate_signal as conservative_signal, get_closes, INTERVAL
from aggressive_scalping_bot import generate_signal as aggressive_signal

# Configuración
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Símbolos para probar (ordenados por volatilidad esperada)
SYMBOLS_TO_TEST = [
    "BTCUSDT",   # Bitcoin (menos volátil)
    "ETHUSDT",   # Ethereum (más volátil)
    "ADAUSDT",   # Cardano (alta volatilidad)
    "SOLUSDT",   # Solana (muy volátil)
    "DOGEUSDT",  # Dogecoin (ultra volátil)
    "SHIBUSDT",  # Shiba Inu (extremadamente volátil)
]

def test_symbol_volatility(symbol):
    """Prueba la volatilidad de un símbolo"""
    try:
        # Obtener datos
        closes = get_closes(symbol, INTERVAL, limit=100)
        current_price = closes[-1]
        
        # Generar señales
        conservative_sig = conservative_signal(closes)
        aggressive_sig = aggressive_signal(closes)
        
        # Calcular volatilidad (desviación estándar de los últimos 20 precios)
        import numpy as np
        recent_prices = closes[-20:]
        volatility = np.std(recent_prices) / np.mean(recent_prices) * 100
        
        return {
            'symbol': symbol,
            'price': current_price,
            'conservative': conservative_sig,
            'aggressive': aggressive_sig,
            'volatility': volatility
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e)
        }

def main():
    """Prueba todos los símbolos"""
    print("🔍 Probando volatilidad de diferentes símbolos...")
    print("=" * 60)
    
    results = []
    
    for symbol in SYMBOLS_TO_TEST:
        print(f"📊 Probando {symbol}...")
        result = test_symbol_volatility(symbol)
        results.append(result)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"💰 Precio: ${result['price']:.2f}")
            print(f"🐌 Conservador: {result['conservative']}")
            print(f"⚡ Agresivo: {result['aggressive']}")
            print(f"📈 Volatilidad: {result['volatility']:.2f}%")
        
        print("-" * 40)
        time.sleep(1)  # Pausa para no sobrecargar la API
    
    # Mostrar resumen
    print("\n📊 RESUMEN DE VOLATILIDAD:")
    print("=" * 60)
    
    valid_results = [r for r in results if 'error' not in r]
    valid_results.sort(key=lambda x: x['volatility'], reverse=True)
    
    for i, result in enumerate(valid_results, 1):
        print(f"{i}. {result['symbol']}: {result['volatility']:.2f}% volatilidad")
        print(f"   Señales: {result['conservative']} / {result['aggressive']}")
    
    # Recomendación
    if valid_results:
        best = valid_results[0]
        print(f"\n🎯 RECOMENDACIÓN: {best['symbol']}")
        print(f"   Mayor volatilidad: {best['volatility']:.2f}%")
        print(f"   Señales actuales: {best['conservative']} / {best['aggressive']}")

if __name__ == "__main__":
    main()
