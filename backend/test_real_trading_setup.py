#!/usr/bin/env python3
"""
Script de prueba para Trading Real con $10 USD
"""

from real_trading_manager import real_trading_manager
import time

def test_real_trading_setup():
    """Prueba la configuración de trading real"""
    
    print("🧪 Probando configuración de Trading Real con $10 USD")
    print("=" * 60)
    
    # Verificar configuración
    status = real_trading_manager.get_trading_status()
    
    print(f"🔧 Modo de trading: {status['trading_mode']}")
    print(f"💰 Tamaño máximo por posición: ${real_trading_manager.max_position_size}")
    print(f"📉 Pérdida máxima diaria: ${real_trading_manager.max_daily_loss}")
    print(f"🔒 Trading habilitado: {status['trading_enabled']}")
    print(f"📊 Posiciones concurrentes máximas: {real_trading_manager.max_concurrent_positions}")
    print()
    
    # Verificar conexión a Binance
    if real_trading_manager.client:
        print("✅ Cliente de Binance inicializado correctamente")
        
        # Obtener balance de cuenta
        balance = real_trading_manager.get_account_balance()
        print(f"💰 Balance de cuenta: {balance}")
        
        # Verificar límites de riesgo
        risk_check = real_trading_manager.check_risk_limits(1.0)  # $1 de prueba
        print(f"🛡️ Verificación de riesgo: {risk_check}")
        
    else:
        print("❌ Cliente de Binance no inicializado")
        print("   Verifica tus API keys en config_real_trading.env")
    
    print("\n" + "=" * 60)
    print("📋 CONFIGURACIÓN RECOMENDADA PARA $10 USD:")
    print("   • Máximo $2 por posición (20% del capital)")
    print("   • Máxima pérdida diaria $5 (50% del capital)")
    print("   • Solo 1 posición a la vez")
    print("   • Stop Loss y Take Profit habilitados")
    print()
    print("⚠️ IMPORTANTE:")
    print("   • Asegúrate de tener al menos $10 USDT en tu cuenta Binance")
    print("   • Las API keys deben tener permisos de Spot Trading")
    print("   • Nunca uses más dinero del que puedes permitirte perder")

if __name__ == "__main__":
    test_real_trading_setup()
