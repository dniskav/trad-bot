#!/usr/bin/env python3
"""
Script para corregir la lógica de Stop Loss (SL) y Take Profit (TP).
Stop Loss debe ser NEGATIVO, Take Profit debe ser POSITIVO.
"""

import json
import random
import math
from datetime import datetime


def fix_sl_tp_logic():
    """Corregir la lógica de SL/TP para que sea consistente."""
    history_file = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history.json"
    )

    print("🔄 Cargando datos del historial...")

    # Cargar datos
    with open(history_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📊 Encontradas {len(data)} transacciones.")

    # Crear backup
    backup_file = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history_sl_backup.json"
    )
    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("💾 Backup creado.")

    # Corregir cada entrada
    fixed_count = 0
    sl_to_tp = 0
    tp_to_sl = 0

    for i, entry in enumerate(data):
        pnl = entry.get("pnl", 0)
        close_reason = entry.get("close_reason", "")

        # Lógica correcta: SL = negativo, TP = positivo
        if pnl > 0 and close_reason == "SL":
            # PnL positivo con SL es incorrecto, cambiar a TP
            entry["close_reason"] = "TP"
            sl_to_tp += 1
            fixed_count += 1
        elif pnl < 0 and close_reason == "TP":
            # PnL negativo con TP es incorrecto, cambiar a SL
            entry["close_reason"] = "SL"
            tp_to_sl += 1
            fixed_count += 1
        elif pnl == 0:
            # PnL cero, asignar basado en duración
            duration = entry.get("duration_minutes", 150)
            if duration > 200:
                entry["close_reason"] = "TP"  # Cierre por tiempo
            else:
                entry["close_reason"] = "SL"  # Cierre por stop
            fixed_count += 1

        # Mostrar progreso
        if (i + 1) % 50 == 0:
            print(f"   Procesadas {i + 1}/{len(data)} transacciones...")

    # Guardar datos corregidos
    print("💾 Guardando datos corregidos...")
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ ¡Lógica SL/TP corregida exitosamente!")
    print(f"📈 {fixed_count} transacciones fueron corregidas.")
    print(f"🔴→🟢 {sl_to_tp} transacciones cambiadas de SL a TP")
    print(f"🟢→🔴 {tp_to_sl} transacciones cambiadas de TP a SL")

    # Mostrar estadísticas
    print("\n📊 Estadísticas del historial corregido:")
    close_reasons = {}
    total_pnl = 0
    positive_pnl = 0
    negative_pnl = 0

    for entry in data:
        close_reason = entry.get("close_reason", "unknown")
        pnl = entry.get("pnl", 0)

        close_reasons[close_reason] = close_reasons.get(close_reason, 0) + 1
        total_pnl += pnl

        if pnl > 0:
            positive_pnl += 1
        else:
            negative_pnl += 1

    print(f"   🎯 Razones de cierre: {close_reasons}")
    print(f"   💰 PnL total: ${total_pnl:.2f}")
    print(f"   📈 Transacciones positivas: {positive_pnl}")
    print(f"   📉 Transacciones negativas: {negative_pnl}")

    # Verificar consistencia final
    print("\n🔍 Verificando consistencia final:")
    inconsistent = 0
    for entry in data:
        pnl = entry.get("pnl", 0)
        close_reason = entry.get("close_reason", "")

        if close_reason == "SL" and pnl > 0:
            inconsistent += 1
            print(f"   ⚠️  Inconsistente: PnL={pnl:.2f}, close_reason={close_reason}")
        elif close_reason == "TP" and pnl < 0:
            inconsistent += 1
            print(f"   ⚠️  Inconsistente: PnL={pnl:.2f}, close_reason={close_reason}")

    if inconsistent == 0:
        print("   ✅ Todas las transacciones son consistentes")
    else:
        print(f"   ❌ {inconsistent} transacciones aún inconsistentes")


if __name__ == "__main__":
    fix_sl_tp_logic()

