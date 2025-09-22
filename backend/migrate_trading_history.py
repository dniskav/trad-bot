#!/usr/bin/env python3
"""
Migración de formato de persistencia:

Convierte el archivo legado logs/trading_history.json en archivos separados:
  - logs/history.json
  - logs/active_positions.json
  - logs/account.json
  - logs/bot_status.json

Uso:
  python3 backend/migrate_trading_history.py

El script detecta automáticamente si el archivo de entrada está en backend/logs o en logs
dependiendo del directorio desde el que se ejecute.
"""

import json
import os
from datetime import datetime


def resolve_log_paths():
    """Resuelve rutas de entrada/salida según cwd actual."""
    candidates = [
        os.path.join("backend", "logs", "trading_history.json"),
        os.path.join("logs", "trading_history.json"),
    ]

    input_path = None
    for c in candidates:
        if os.path.exists(c):
            input_path = c
            break

    if not input_path:
        raise FileNotFoundError(
            "No se encontró trading_history.json en backend/logs ni logs. Ejecuta el script desde la raíz del repo."
        )

    base_dir = os.path.dirname(input_path)

    return {
        "input": input_path,
        "history": os.path.join(base_dir, "history.json"),
        "active": os.path.join(base_dir, "active_positions.json"),
        "account": os.path.join(base_dir, "account.json"),
        "bot_status": os.path.join(base_dir, "bot_status.json"),
    }


def safe_write(path: str, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w") as tf:
        json.dump(payload, tf, indent=2, default=str)
    os.replace(tmp_path, path)


def migrate():
    paths = resolve_log_paths()

    with open(paths["input"], "r") as f:
        data = json.load(f)

    # Extraer con defaults sensatos
    history = data.get("history", [])
    active_positions = data.get("active_positions", {})
    bot_status = data.get("bot_status", {})
    account = {
        "initial_balance": data.get("initial_balance", 0.0),
        "current_balance": data.get("current_balance", 0.0),
        "total_pnl": data.get("total_pnl", 0.0),
        "last_updated": datetime.now().isoformat(),
    }

    # Escribir archivos separados
    safe_write(paths["history"], history)
    safe_write(paths["active"], active_positions)
    safe_write(paths["account"], account)
    safe_write(paths["bot_status"], bot_status)

    print("✅ Migración completada:")
    print(f"  - {paths['history']}")
    print(f"  - {paths['active']}")
    print(f"  - {paths['account']}")
    print(f"  - {paths['bot_status']}")


if __name__ == "__main__":
    migrate()


