#!/usr/bin/env python3
"""
Script para probar la configuración de Binance con ADAUSDT
"""

from real_trading_manager import real_trading_manager
import time

def test_binance_connection():
    """Prueba la conexión con Binance y configuración para ADAUSDT"""
    
    print("🧪 Probando conexión con Binance para ADAUSDT")
    print("=" * 60)
    
    # Verificar configuración
    status = real_trading_manager.get_trading_status()
    
    print(f"🔧 Modo de trading: {status['trading_mode']}")
    print(f"💰 Tamaño máximo por posición: ${real_trading_manager.max_position_size}")
    print(f"📉 Pérdida máxima diaria: ${real_trading_manager.max_daily_loss}")
    print(f"🔒 Trading habilitado: {status['trading_enabled']}")
    print()
    
    # Verificar conexión a Binance
    if real_trading_manager.client:
        print("✅ Cliente de Binance inicializado")
        
        try:
            # Obtener balance de USDT
            balance = real_trading_manager.get_account_balance()
            print(f"💰 Balance de cuenta: {balance}")
            
            # Obtener precio actual de ADAUSDT
            current_price = real_trading_manager.get_current_price("ADAUSDT")
            print(f"📊 Precio actual ADAUSDT: ${current_price}")
            
            # Calcular cuántos ADA puedes comprar con $2
            if isinstance(current_price, (int, float)) and current_price > 0:
                ada_amount = 2.0 / current_price
                print(f"🪙 Con $2 puedes comprar: {ada_amount:.2f} ADA")
            
            # Verificar límites de riesgo
            risk_check = real_trading_manager.check_risk_limits(2.0)  # $2 de prueba
            print(f"🛡️ Verificación de riesgo: {risk_check}")
            
        except Exception as e:
            print(f"❌ Error conectando con Binance: {e}")
            print("   Verifica tus API keys en config_real_trading.env")
    
    else:
        print("❌ Cliente de Binance no inicializado")
        print("   Verifica tus API keys en config_real_trading.env")
    
    print("\n" + "=" * 60)
    print("📋 CONFIGURACIÓN PARA ADAUSDT CON $10 USD:")
    print("   • Deposita $10 USDT en Binance")
    print("   • Configura API keys con permisos de Spot Trading")
    print("   • Máximo $2 por posición (20% del capital)")
    print("   • Máxima pérdida diaria $5 (50% del capital)")
    print("   • Solo 1 posición a la vez")
    print()
    print("⚠️ IMPORTANTE:")
    print("   • ADAUSDT es volátil, perfecto para scalping")
    print("   • El bot comprará/venderá ADA usando USDT")
    print("   • Nunca uses más dinero del que puedes permitirte perder")

if __name__ == "__main__":
    test_binance_connection()
