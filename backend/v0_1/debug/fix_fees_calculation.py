#!/usr/bin/env python3
"""
Script para corregir el cálculo de fees_paid en el historial de transacciones.
Todas las transacciones deben tener fees realistas de Binance, incluso las sintéticas.
"""

import json
import random
import math
from datetime import datetime

def calculate_binance_fees(entry_price: float, close_price: float, quantity: float) -> float:
    """
    Calcula fees realistas de Binance para una transacción completa.
    
    Binance fees (con BNB discount):
    - Maker: 0.075% (0.00075)
    - Taker: 0.075% (0.00075)
    - Total por transacción completa: ~0.15% (0.0015)
    """
    # Valor de la transacción de entrada
    entry_value = entry_price * quantity
    
    # Valor de la transacción de salida  
    exit_value = close_price * quantity
    
    # Fee de entrada (taker/maker)
    entry_fee = entry_value * 0.00075  # 0.075%
    
    # Fee de salida (taker/maker)
    exit_fee = exit_value * 0.00075   # 0.075%
    
    # Total fees
    total_fees = entry_fee + exit_fee
    
    return round(total_fees, 6)

def fix_fees_in_history():
    """Corregir fees_paid en todas las transacciones del historial."""
    history_file = "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history.json"
    
    print("🔄 Cargando datos del historial...")
    
    # Cargar datos
    with open(history_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"📊 Encontradas {len(data)} transacciones.")
    
    # Crear backup
    backup_file = "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history_fees_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("💾 Backup creado.")
    
    # Corregir cada entrada
    fixed_count = 0
    total_fees_before = 0
    total_fees_after = 0
    
    for i, entry in enumerate(data):
        original_fees = entry.get("fees_paid", 0)
        total_fees_before += original_fees
        
        # Obtener datos de la transacción
        entry_price = entry.get("entry_price", 0)
        close_price = entry.get("close_price", 0)
        quantity = entry.get("quantity", 0)
        
        if entry_price > 0 and close_price > 0 and quantity > 0:
            # Calcular fees realistas de Binance
            realistic_fees = calculate_binance_fees(entry_price, close_price, quantity)
            
            # Actualizar fees
            entry["fees_paid"] = realistic_fees
            total_fees_after += realistic_fees
            
            # Recalcular net_pnl considerando los fees
            pnl = entry.get("pnl", 0)
            entry["net_pnl"] = round(pnl - realistic_fees, 6)
            
            # Verificar si se hicieron cambios significativos
            if abs(original_fees - realistic_fees) > 0.001:
                fixed_count += 1
        
        # Mostrar progreso
        if (i + 1) % 50 == 0:
            print(f"   Procesadas {i + 1}/{len(data)} transacciones...")
    
    # Guardar datos corregidos
    print("💾 Guardando datos corregidos...")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ ¡Fees corregidos exitosamente!")
    print(f"📈 {fixed_count} transacciones fueron corregidas.")
    print(f"💰 Fees antes: ${total_fees_before:.2f}")
    print(f"💰 Fees después: ${total_fees_after:.2f}")
    print(f"💰 Diferencia: ${total_fees_after - total_fees_before:.2f}")
    
    # Mostrar estadísticas de fees
    print("\n📊 Estadísticas de fees:")
    fees_by_bot = {}
    total_pnl_gross = 0
    total_pnl_net = 0
    
    for entry in data:
        bot_type = entry.get("bot_type", "unknown")
        fees = entry.get("fees_paid", 0)
        pnl = entry.get("pnl", 0)
        net_pnl = entry.get("net_pnl", 0)
        
        fees_by_bot[bot_type] = fees_by_bot.get(bot_type, 0) + fees
        total_pnl_gross += pnl
        total_pnl_net += net_pnl
    
    print(f"   💸 Fees por bot: {fees_by_bot}")
    print(f"   📈 PnL bruto total: ${total_pnl_gross:.2f}")
    print(f"   📉 PnL neto total: ${total_pnl_net:.2f}")
    print(f"   💸 Fees totales: ${total_pnl_gross - total_pnl_net:.2f}")
    
    # Verificar consistencia
    print("\n🔍 Verificando consistencia de fees:")
    inconsistent = 0
    zero_fees = 0
    
    for entry in data:
        fees = entry.get("fees_paid", 0)
        entry_price = entry.get("entry_price", 0)
        close_price = entry.get("close_price", 0)
        quantity = entry.get("quantity", 0)
        
        if fees == 0:
            zero_fees += 1
        
        # Verificar si los fees son realistas (aproximadamente 0.15% del valor total)
        if entry_price > 0 and close_price > 0 and quantity > 0:
            total_value = (entry_price + close_price) * quantity
            expected_fees = total_value * 0.0015  # 0.15%
            
            if abs(fees - expected_fees) > expected_fees * 0.5:  # 50% de tolerancia
                inconsistent += 1
    
    if zero_fees == 0:
        print("   ✅ No hay transacciones con fees en 0")
    else:
        print(f"   ⚠️  {zero_fees} transacciones aún tienen fees en 0")
    
    if inconsistent == 0:
        print("   ✅ Todos los fees son consistentes")
    else:
        print(f"   ⚠️  {inconsistent} transacciones tienen fees inconsistentes")

if __name__ == "__main__":
    fix_fees_in_history()

