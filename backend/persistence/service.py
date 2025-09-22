from typing import Dict, Any, List

from .ports import PersistencePort


class PersistenceService:
    """Servicio de aplicación que orquesta la persistencia a través del puerto configurado."""

    def __init__(self, repo: PersistencePort):
        self.repo = repo

    # Facades de lectura
    def get_history(self) -> List[Dict[str, Any]]:
        return self.repo.load_history()

    def get_active_positions(self) -> Dict[str, Dict[str, Any]]:
        return self.repo.load_active_positions()

    def get_account(self) -> Dict[str, Any]:
        return self.repo.load_account()

    def get_bot_status(self) -> Dict[str, bool]:
        return self.repo.load_bot_status()

    # Facades de escritura
    def set_history(self, history: List[Dict[str, Any]]) -> None:
        self.repo.save_history(history)

    def set_active_positions(self, active: Dict[str, Dict[str, Any]]) -> None:
        self.repo.save_active_positions(active)

    def set_account(self, account: Dict[str, Any]) -> None:
        self.repo.save_account(account)

    def set_bot_status(self, status: Dict[str, bool]) -> None:
        self.repo.save_bot_status(status)

    # Snapshots (operaciones agrupadas)
    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "history": self.get_history(),
            "active_positions": self.get_active_positions(),
            "account": self.get_account(),
            "bot_status": self.get_bot_status(),
        }

    def save_snapshot(self, *, history=None, active_positions=None, account=None, bot_status=None) -> None:
        if history is not None:
            self.set_history(history)
        if active_positions is not None:
            self.set_active_positions(active_positions)
        if account is not None:
            self.set_account(account)
        if bot_status is not None:
            self.set_bot_status(bot_status)


