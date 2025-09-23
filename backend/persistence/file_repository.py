import json
import os
from typing import Any, Dict, List
from datetime import datetime

from .ports import PersistencePort


class FilePersistenceRepository(PersistencePort):
    """Repositorio basado en archivos JSON (nuevo formato separado)."""

    def __init__(self, base_dir: str = "logs"):
        self.base_dir = base_dir
        self.history_path = os.path.join(base_dir, "history.json")
        self.active_path = os.path.join(base_dir, "active_positions.json")
        self.account_path = os.path.join(base_dir, "account.json")
        self.bot_status_path = os.path.join(base_dir, "bot_status.json")
        self.bot_configs_path = os.path.join(base_dir, "bot_configs.json")

        os.makedirs(self.base_dir, exist_ok=True)

    # ------------- helpers -------------
    def _safe_write(self, path: str, payload: Any) -> None:
        tmp = f"{path}.tmp"
        with open(tmp, "w") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, path)

    def _read_json(self, path: str, default):
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    # ------------- history -------------
    def load_history(self) -> List[Dict[str, Any]]:
        return self._read_json(self.history_path, [])

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        self._safe_write(self.history_path, history)

    # -------- active positions --------
    def load_active_positions(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(self.active_path, {})

    def save_active_positions(self, active: Dict[str, Dict[str, Any]]) -> None:
        self._safe_write(self.active_path, active)

    # ------------- account -------------
    def load_account(self) -> Dict[str, Any]:
        return self._read_json(self.account_path, {
            "initial_balance": 0.0,
            "current_balance": 0.0,
            "total_pnl": 0.0,
            "last_updated": datetime.now().isoformat()
        })

    def save_account(self, account: Dict[str, Any]) -> None:
        if "last_updated" not in account:
            account["last_updated"] = datetime.now().isoformat()
        self._safe_write(self.account_path, account)

    # ---------- bot status ------------
    def load_bot_status(self) -> Dict[str, bool]:
        return self._read_json(self.bot_status_path, {"conservative": False, "aggressive": False})

    def save_bot_status(self, status: Dict[str, bool]) -> None:
        self._safe_write(self.bot_status_path, status)

    # ---------- bot configs ------------
    def load_bot_configs(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(self.bot_configs_path, {})

    def save_bot_configs(self, configs: Dict[str, Dict[str, Any]]) -> None:
        self._safe_write(self.bot_configs_path, configs)


