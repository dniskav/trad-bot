#!/usr/bin/env python3
"""
Demostración del sistema de bots plug-and-play
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_registry import bot_registry
from bot_interface import MarketData
from bots.rsi_bot import create_rsi_bot
from bots.macd_bot import create_macd_bot
import numpy as np

def create_sample_market_data():
    """Crea datos de mercado de ejemplo"""
    # Generar datos sintéticos para demostración
    np.random.seed(42)
    n_points = 100
    
    # Precios base con tendencia
    base_price = 0.25
    trend = np.linspace(0, 0.05, n_points)
    noise = np.random.normal(0, 0.01, n_points)
    closes = base_price + trend + noise
    
    # Generar highs, lows y volumes
    highs = closes + np.random.uniform(0, 0.005, n_points)
    lows = closes - np.random.uniform(0, 0.005, n_points)
    volumes = np.random.uniform(1000000, 5000000, n_points)
    timestamps = list(range(1000, 1000 + n_points))
    
    return MarketData(
        symbol="DOGEUSDT",
        interval="1m",
        closes=closes.tolist(),
        highs=highs.tolist(),
        lows=lows.tolist(),
        volumes=volumes.tolist(),
        timestamps=timestamps,
        current_price=closes[-1]
    )

def main():
    """Función principal de demostración"""
    print("🚀 Demostración del Sistema de Bots Plug-and-Play")
    print("=" * 60)
    
    # 1. Mostrar bots existentes
    print("\n📋 Bots existentes en el sistema:")
    existing_bots = bot_registry.get_all_bots()
    for name, bot in existing_bots.items():
        status = bot.get_status()
        print(f"  • {name}: {status['description']}")
        print(f"    Versión: {status['version']}, Autor: {status['author']}")
        print(f"    Activo: {status['is_active']}, Posiciones: {status['positions_count']}")
    
    # 2. Crear y registrar nuevos bots
    print("\n🔧 Creando nuevos bots...")
    
    # Bot RSI personalizado
    rsi_bot = create_rsi_bot(
        name="rsi_aggressive",
        rsi_period=10,
        oversold_threshold=25,
        overbought_threshold=75,
        risk_level="high"
    )
    bot_registry.register_bot(rsi_bot)
    print(f"✅ Bot RSI registrado: {rsi_bot.config.name}")
    
    # Bot MACD personalizado
    macd_bot = create_macd_bot(
        name="macd_scalping",
        fast_period=8,
        slow_period=21,
        signal_period=5,
        risk_level="high"
    )
    bot_registry.register_bot(macd_bot)
    print(f"✅ Bot MACD registrado: {macd_bot.config.name}")
    
    # 3. Activar algunos bots
    print("\n🚀 Activando bots...")
    bot_registry.start_bot("rsi_aggressive")
    bot_registry.start_bot("macd_scalping")
    bot_registry.start_bot("conservative")  # Bot legacy
    
    # 4. Crear datos de mercado de ejemplo
    print("\n📊 Creando datos de mercado de ejemplo...")
    market_data = create_sample_market_data()
    print(f"  Precio actual: ${market_data.current_price:.5f}")
    print(f"  Datos disponibles: {len(market_data.closes)} puntos")
    
    # 5. Ejecutar análisis de todos los bots activos
    print("\n🔍 Ejecutando análisis de bots activos...")
    signals = bot_registry.analyze_all_bots(market_data)
    
    for bot_name, signal_data in signals.items():
        if 'error' in signal_data:
            print(f"  ❌ {bot_name}: Error - {signal_data['error']}")
        else:
            signal_type = signal_data['signal_type']
            confidence = signal_data['confidence']
            reasoning = signal_data['reasoning']
            print(f"  📈 {bot_name}: {signal_type} (confianza: {confidence:.2f})")
            print(f"      Razón: {reasoning}")
    
    # 6. Mostrar estado final
    print("\n📊 Estado final del sistema:")
    all_bots = bot_registry.get_all_bots()
    active_bots = bot_registry.get_active_bots()
    
    print(f"  Total de bots: {len(all_bots)}")
    print(f"  Bots activos: {len(active_bots)}")
    print(f"  Bots inactivos: {len(all_bots) - len(active_bots)}")
    
    print("\n🤖 Lista completa de bots:")
    for name, bot in all_bots.items():
        status = "🟢 Activo" if bot.is_active else "🔴 Inactivo"
        print(f"  • {name}: {status}")
    
    # 7. Demostrar métricas de rendimiento
    print("\n📈 Métricas de rendimiento:")
    for name, bot in active_bots.items():
        metrics = bot.get_performance_metrics()
        print(f"  {name}:")
        print(f"    Trades totales: {metrics['total_trades']}")
        print(f"    Posiciones activas: {metrics['active_positions']}")
        print(f"    Última señal: {metrics.get('last_signal_time', 'N/A')}")
    
    print("\n✅ Demostración completada!")
    print("\n💡 Para usar el sistema:")
    print("  1. Crea nuevos bots heredando de BaseBot")
    print("  2. Colócalos en el directorio bots/")
    print("  3. El sistema los cargará automáticamente")
    print("  4. Actívalos desde el frontend o terminal")

if __name__ == "__main__":
    main()
