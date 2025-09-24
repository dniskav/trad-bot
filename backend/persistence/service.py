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

    # Accounts
    def get_account_real(self) -> Dict[str, Any]:
        return self.repo.load_account_real()

    def get_account_synth(self) -> Dict[str, Any]:
        return self.repo.load_account_synth()

    def get_bot_status(self) -> Dict[str, bool]:
        return self.repo.load_bot_status()

    def get_bot_configs(self) -> Dict[str, Dict[str, Any]]:
        return self.repo.load_bot_configs()

    # Facades de escritura
    def set_history(self, history: List[Dict[str, Any]]) -> None:
        self.repo.save_history(history)

    def set_active_positions(self, active: Dict[str, Dict[str, Any]]) -> None:
        self.repo.save_active_positions(active)

    def set_account_real(self, account: Dict[str, Any]) -> None:
        self.repo.save_account_real(account)

    def set_account_synth(self, account: Dict[str, Any]) -> None:
        self.repo.save_account_synth(account)

    def set_bot_status(self, status: Dict[str, bool]) -> None:
        self.repo.save_bot_status(status)

    def set_bot_configs(self, configs: Dict[str, Dict[str, Any]]) -> None:
        self.repo.save_bot_configs(configs)

    # Snapshots (operaciones agrupadas)
    def get_snapshot(self) -> Dict[str, Any]:
        return {
            "history": self.get_history(),
            "active_positions": self.get_active_positions(),
            "account_real": self.get_account_real(),
            "account_synth": self.get_account_synth(),
            "bot_status": self.get_bot_status(),
            "bot_configs": self.get_bot_configs(),
        }

    def save_snapshot(
        self,
        *,
        history=None,
        active_positions=None,
        account_real=None,
        account_synth=None,
        bot_status=None,
        bot_configs=None
    ) -> None:
        if history is not None:
            self.set_history(history)
        if active_positions is not None:
            self.set_active_positions(active_positions)
        if account_real is not None:
            self.set_account_real(account_real)
        if account_synth is not None:
            self.set_account_synth(account_synth)
        if bot_status is not None:
            self.set_bot_status(bot_status)
        if bot_configs is not None:
            self.set_bot_configs(bot_configs)
