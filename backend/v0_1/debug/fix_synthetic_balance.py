#!/usr/bin/env python3
"""
Script para corregir el saldo synthetic eliminando los fondos bloqueados incorrectos
y reseteando a un estado limpio.
"""

import json
import os
from datetime import datetime


def fix_synthetic_balance():
    """Corrige el saldo synthetic eliminando fondos bloqueados incorrectos"""

    account_synth_path = "logs/account_synth.json"

    print("🔧 Corrigiendo saldo synthetic...")

    # Leer datos actuales
    try:
        with open(account_synth_path, "r") as f:
            current_data = json.load(f)
    except FileNotFoundError:
        print("❌ No se encontró account_synth.json")
        return False

    print(f"📊 Datos actuales:")
    print(f"   Saldo inicial: ${current_data.get('initial_balance', 0):.2f}")
    print(f"   Saldo actual: ${current_data.get('current_balance', 0):.2f}")
    print(f"   USDT disponible: ${current_data.get('usdt_balance', 0):.2f}")
    print(f"   DOGE disponible: {current_data.get('doge_balance', 0):.4f}")
    print(f"   USDT bloqueado: ${current_data.get('usdt_locked', 0):.2f}")
    print(f"   DOGE bloqueado: {current_data.get('doge_locked', 0):.4f}")

    # Calcular saldo real sin fondos bloqueados
    doge_price = current_data.get("doge_price", 0.24215)
    usdt_available = current_data.get("usdt_balance", 0)
    doge_available = current_data.get("doge_balance", 0)

    real_balance = usdt_available + (doge_available * doge_price)

    print(f"\n💰 Saldo real (sin bloqueados): ${real_balance:.2f}")
    print(f"📈 Ganancia real: ${real_balance - 1000:.2f}")

    # Crear nuevo saldo corregido
    corrected_data = {
        "initial_balance": 1000.0,
        "current_balance": real_balance,
        "total_pnl": real_balance - 1000.0,
        "usdt_balance": usdt_available,
        "doge_balance": doge_available,
        "usdt_locked": 0.0,  # Eliminar fondos bloqueados
        "doge_locked": 0.0,  # Eliminar fondos bloqueados
        "doge_price": doge_price,
        "total_balance_usdt": real_balance,
        "last_updated": datetime.now().isoformat(),
    }

    # Hacer backup
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
        print(f"✅ Saldo synthetic corregido")
        print(f"   Nuevo saldo: ${real_balance:.2f}")
        print(f"   Ganancia: ${real_balance - 1000:.2f}")
        return True
    except Exception as e:
        print(f"❌ Error guardando datos corregidos: {e}")
        return False


if __name__ == "__main__":
    success = fix_synthetic_balance()
    if success:
        print("\n🎉 Corrección completada exitosamente")
    else:
        print("\n💥 Error en la corrección")
