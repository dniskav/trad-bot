#!/usr/bin/env python3
"""
Script para corregir el total_pnl en account_synth.json
basándose en el historial real de trades
"""

import json
import os
from datetime import datetime


def fix_total_pnl():
    account_synth_path = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/account_synth.json"
    )
    history_path = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/history.json"
    )

    print("🔧 Corrigiendo cálculo del total_pnl...")

    try:
        with open(account_synth_path, "r") as f:
            account_data = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró account_synth.json")
        return False

    try:
        with open(history_path, "r") as f:
            history_data = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró history.json")
        return False

    print(f"📊 Datos actuales:")
    print(f"   Saldo inicial: ${account_data.get('initial_balance', 0):.2f}")
    print(f"   Saldo disponible: ${account_data.get('current_balance', 0):.2f}")
    print(f"   Total PnL actual: ${account_data.get('total_pnl', 0):.2f}")
    print()

    # Calcular PnL real desde el historial
    total_pnl_real = 0.0
    if history_data and len(history_data) > 0:
        print(f"📋 Analizando {len(history_data)} trades:")
        for i, trade in enumerate(history_data, 1):
            pnl = trade.get("pnl", 0)
            total_pnl_real += pnl
            bot_type = trade.get("bot_type", "N/A")
            side = trade.get("side", "N/A")
            print(f"   {i}. {bot_type} {side}: ${pnl:.4f}")

        print(f"\n💰 PnL total calculado: ${total_pnl_real:.4f}")
    else:
        print("⚠️ No hay historial de trades")
        total_pnl_real = 0.0

    # Calcular el saldo disponible correcto
    initial_balance = account_data.get("initial_balance", 1000.0)
    correct_current_balance = initial_balance + total_pnl_real

    print(f"\n🔧 Correcciones necesarias:")
    print(f"   PnL actual: ${account_data.get('total_pnl', 0):.2f}")
    print(f"   PnL real: ${total_pnl_real:.4f}")
    print(f"   Saldo actual: ${account_data.get('current_balance', 0):.2f}")
    print(f"   Saldo correcto: ${correct_current_balance:.2f}")

    # Crear datos corregidos
    corrected_data = account_data.copy()
    corrected_data["total_pnl"] = total_pnl_real
    corrected_data["current_balance"] = correct_current_balance
    corrected_data["total_balance_usdt"] = correct_current_balance
    corrected_data["last_updated"] = datetime.now().isoformat()

    # Crear backup
    backup_path = (
        f"{account_synth_path}.backup_pnl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    try:
        with open(backup_path, "w") as f:
            json.dump(account_data, f, indent=2)
        print(f"\n💾 Backup creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear backup: {e}")

    # Guardar datos corregidos
    try:
        with open(account_synth_path, "w") as f:
            json.dump(corrected_data, f, indent=2)
        print(f"\n✅ PnL corregido exitosamente")
        print(f"   Nuevo PnL: ${corrected_data['total_pnl']:.4f}")
        print(f"   Nuevo saldo: ${corrected_data['current_balance']:.2f}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar datos corregidos: {e}")
        return False


if __name__ == "__main__":
    success = fix_total_pnl()
    if success:
        print("\n🎉 Corrección del PnL completada exitosamente")
    else:
        print("\n💥 Error en la corrección del PnL")
