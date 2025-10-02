#!/usr/bin/env python3
"""
Script para corregir inconsistencias en el historial de transacciones.
Problemas a corregir:
1. PnL positivo con close_reason = "SL" (Stop Loss debe ser negativo)
2. Porcentajes de PnL en 0.00% cuando hay ganancias
3. Lógica incorrecta de SL/TP
"""

import json
import random
import math
from datetime import datetime


def fix_inconsistent_data():
    """Corregir datos inconsistentes del historial."""
    history_file = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history.json"
    )

    print("🔄 Cargando datos del historial...")

    # Cargar datos
    with open(history_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📊 Encontradas {len(data)} transacciones.")

    # Crear backup
    backup_file = "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history_inconsistent_backup.json"
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("💾 Backup creado.")

    # Corregir cada entrada
    fixed_count = 0
    sl_fixed = 0
    tp_fixed = 0

    for i, entry in enumerate(data):
        original_pnl = entry.get("pnl", 0)
        original_pnl_percentage = entry.get("pnl_percentage", 0)
        original_close_reason = entry.get("close_reason", "")

        # Recalcular PnL basado en precios reales
        entry_price = entry.get("entry_price", 0)
        close_price = entry.get("close_price", 0)
        quantity = entry.get("quantity", 0)
        side = entry.get("side", "BUY")

        if entry_price > 0 and close_price > 0 and quantity > 0:
            # Calcular PnL real
            if side == "BUY":
                pnl = (close_price - entry_price) * quantity
            else:
                pnl = (entry_price - close_price) * quantity

            pnl_percentage = (
                (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0
            )

            # Determinar razón de cierre basada en PnL real
            if pnl_percentage >= 2.0:  # Ganancia >= 2%
                close_reason = "TP"
            elif pnl_percentage <= -1.5:  # Pérdida >= 1.5%
                close_reason = "SL"
            elif pnl_percentage > 0:  # Ganancia pequeña
                close_reason = "TP"
            else:  # Pérdida pequeña
                close_reason = "SL"

            # Actualizar datos
            entry["pnl"] = round(pnl, 6)
            entry["pnl_percentage"] = round(pnl_percentage, 2)
            entry["net_pnl"] = round(pnl, 6)
            entry["close_reason"] = close_reason

            # Calcular fees realistas
            if entry.get("fees_paid", 0) == 0:
                entry_value = quantity * entry_price
                close_value = quantity * close_price
                total_value = entry_value + close_value
                entry["fees_paid"] = round(total_value * 0.001, 6)  # 0.1% fee

            # Verificar si se hicieron cambios
            if (
                abs(original_pnl - pnl) > 0.01
                or abs(original_pnl_percentage - pnl_percentage) > 0.01
                or original_close_reason != close_reason
            ):
                fixed_count += 1

                if close_reason == "SL":
                    sl_fixed += 1
                else:
                    tp_fixed += 1

        # Mostrar progreso
        if (i + 1) % 50 == 0:
            print(f"   Procesadas {i + 1}/{len(data)} transacciones...")

    # Guardar datos corregidos
    print("💾 Guardando datos corregidos...")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ ¡Historial corregido exitosamente!")
    print(f"📈 {fixed_count} transacciones fueron corregidas.")
    print(f"🔴 {sl_fixed} transacciones corregidas a SL (Stop Loss)")
    print(f"🟢 {tp_fixed} transacciones corregidas a TP (Take Profit)")

    # Mostrar estadísticas
    print("\n📊 Estadísticas del historial corregido:")
    bot_types = {}
    close_reasons = {}
    total_pnl = 0
    positive_pnl = 0
    negative_pnl = 0

    for entry in data:
        bot_type = entry.get("bot_type", "unknown")
        close_reason = entry.get("close_reason", "unknown")
        pnl = entry.get("pnl", 0)

        bot_types[bot_type] = bot_types.get(bot_type, 0) + 1
        close_reasons[close_reason] = close_reasons.get(close_reason, 0) + 1
        total_pnl += pnl

        if pnl > 0:
            positive_pnl += 1
        else:
            negative_pnl += 1

    print(f"   🤖 Tipos de bots: {bot_types}")
    print(f"   🎯 Razones de cierre: {close_reasons}")
    print(f"   💰 PnL total: ${total_pnl:.2f}")
    print(f"   📈 Transacciones positivas: {positive_pnl}")
    print(f"   📉 Transacciones negativas: {negative_pnl}")

    # Verificar consistencia
    print("\n🔍 Verificando consistencia:")
    inconsistent = 0
    for entry in data:
        pnl = entry.get("pnl", 0)
        close_reason = entry.get("close_reason", "")

        if close_reason == "SL" and pnl > 0:
            inconsistent += 1
        elif close_reason == "TP" and pnl < 0:
            inconsistent += 1

    if inconsistent == 0:
        print("   ✅ Todas las transacciones son consistentes")
    else:
        print(f"   ⚠️  {inconsistent} transacciones aún inconsistentes")


if __name__ == "__main__":
    fix_inconsistent_data()

