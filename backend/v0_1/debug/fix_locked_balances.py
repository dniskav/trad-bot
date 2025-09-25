#!/usr/bin/env python3
"""
Script para corregir saldos bloqueados en account_synth.json
"""

import json
import os
from datetime import datetime


def fix_locked_balances():
    account_synth_path = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/account_synth.json"
    )
    print("🔧 Corrigiendo saldos bloqueados...")

    try:
        with open(account_synth_path, "r") as f:
            current_data = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró account_synth.json")
        return False

    print(f"📊 Datos actuales:")
    print(f"   Saldo inicial: ${current_data.get('initial_balance', 0):.2f}")
    print(f"   Saldo disponible: ${current_data.get('current_balance', 0):.2f}")
    print(f"   USDT disponible: ${current_data.get('usdt_balance', 0):.2f}")
    print(f"   DOGE disponible: {current_data.get('doge_balance', 0):.4f}")
    print(f"   USDT bloqueado: ${current_data.get('usdt_locked', 0):.2f}")
    print(f"   DOGE bloqueado: {current_data.get('doge_locked', 0):.4f}")
    print(f"   Invertido: ${current_data.get('invested', 0):.2f}")

    # Leer posiciones activas para calcular el invertido correcto
    try:
        with open(
            "/Users/daniel/Desktop/projects/trading_bot/backend/logs/active_positions.json",
            "r",
        ) as f:
            positions = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró active_positions.json")
        return False

    # Calcular invertido real
    invested_amount = 0.0
    for bot_type, bot_positions in positions.items():
        if isinstance(bot_positions, dict):
            for pos_id, pos_data in bot_positions.items():
                if (
                    pos_data.get("status") == "open"
                    and not pos_data.get("is_closed", False)
                    and pos_data.get("close_reason") is None
                ):

                    current_price = pos_data.get(
                        "current_price", pos_data.get("entry_price", 0)
                    )
                    quantity = pos_data.get("quantity", 0)
                    invested_amount += current_price * quantity

    print(f"\n💰 Cálculos:")
    print(f"   Invertido calculado: ${invested_amount:.2f}")
    print(f"   Invertido en archivo: ${current_data.get('invested', 0):.2f}")

    # Corregir datos
    doge_price = current_data.get("doge_price", 0.24079)
    usdt_available = current_data.get("usdt_balance", 0)
    doge_available = current_data.get("doge_balance", 0)

    # El saldo disponible debería ser la suma de USDT + DOGE disponibles
    available_balance = usdt_available + (doge_available * doge_price)

    corrected_data = {
        "initial_balance": float(current_data.get("initial_balance", 1000.0)),
        "current_balance": available_balance,
        "total_pnl": available_balance
        - float(current_data.get("initial_balance", 1000.0)),
        "usdt_balance": usdt_available,
        "doge_balance": doge_available,
        "usdt_locked": 0.0,  # CORREGIR: Desbloquear USDT
        "doge_locked": 0.0,  # CORREGIR: Desbloquear DOGE
        "doge_price": doge_price,
        "total_balance_usdt": available_balance,
        "invested": invested_amount,  # Usar el valor calculado
        "last_updated": datetime.now().isoformat(),
    }

    # Crear backup
    backup_path = (
        f"{account_synth_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    try:
        with open(backup_path, "w") as f:
            json.dump(current_data, f, indent=2)
        print(f"💾 Backup creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear backup: {e}")

    # Guardar datos corregidos
    try:
        with open(account_synth_path, "w") as f:
            json.dump(corrected_data, f, indent=2)
        print(f"✅ Saldos bloqueados corregidos")
        print(f"   Nuevo saldo disponible: ${corrected_data['current_balance']:.2f}")
        print(f"   USDT bloqueado: ${corrected_data['usdt_locked']:.2f}")
        print(f"   DOGE bloqueado: {corrected_data['doge_locked']:.4f}")
        print(f"   Invertido: ${corrected_data['invested']:.2f}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar saldo corregido: {e}")
        return False


if __name__ == "__main__":
    success = fix_locked_balances()
    if success:
        print("\n🎉 Corrección completada exitosamente")
    else:
        print("\n💥 Error en la corrección")
