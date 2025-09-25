#!/usr/bin/env python3
"""
Script para corregir saldos bloqueados negativos
"""

import json
import os
from datetime import datetime


def fix_negative_locked_balances():
    account_synth_path = (
        "/Users/daniel/Desktop/projects/trading_bot/backend/logs/account_synth.json"
    )

    print("🔧 Corrigiendo saldos bloqueados negativos...")

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

    # Verificar si hay saldos bloqueados incorrectos
    usdt_locked = current_data.get("usdt_locked", 0)
    doge_locked = current_data.get("doge_locked", 0)

    print(f"\n🔍 ANÁLISIS:")
    if usdt_locked != 0:
        print(f"   ❌ USDT bloqueado: ${usdt_locked:.2f} (debería ser 0.00)")
    if doge_locked != 0:
        print(f"   ❌ DOGE bloqueado: {doge_locked:.4f} (debería ser 0.0000)")

    if usdt_locked < 0 or doge_locked < 0:
        print(f"   ❌ VALORES NEGATIVOS DETECTADOS")
        print(f"   ❌ Los saldos bloqueados no pueden ser negativos")

    # Corregir datos
    corrected_data = current_data.copy()
    corrected_data["usdt_locked"] = (
        0.0  # CORREGIR: Siempre debe ser 0 si no hay posiciones activas
    )
    corrected_data["doge_locked"] = (
        0.0  # CORREGIR: Siempre debe ser 0 si no hay posiciones activas
    )
    corrected_data["last_updated"] = datetime.now().isoformat()

    print(f"\n🔧 CORRECCIONES:")
    print(
        f"   USDT bloqueado: ${usdt_locked:.2f} → ${corrected_data['usdt_locked']:.2f}"
    )
    print(f"   DOGE bloqueado: {doge_locked:.4f} → {corrected_data['doge_locked']:.4f}")

    # Crear backup
    backup_path = f"{account_synth_path}.backup_negative_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        with open(backup_path, "w") as f:
            json.dump(current_data, f, indent=2)
        print(f"\n💾 Backup creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ No se pudo crear backup: {e}")

    # Guardar datos corregidos
    try:
        with open(account_synth_path, "w") as f:
            json.dump(corrected_data, f, indent=2)
        print(f"\n✅ Saldos bloqueados corregidos")
        print(f"   USDT bloqueado: ${corrected_data['usdt_locked']:.2f}")
        print(f"   DOGE bloqueado: {corrected_data['doge_locked']:.4f}")
        return True
    except Exception as e:
        print(f"❌ Error al guardar datos corregidos: {e}")
        return False


if __name__ == "__main__":
    success = fix_negative_locked_balances()
    if success:
        print("\n🎉 Corrección completada exitosamente")
        print("🎯 Los saldos bloqueados ahora son 0.0 como debería ser")
    else:
        print("\n💥 Error en la corrección")
