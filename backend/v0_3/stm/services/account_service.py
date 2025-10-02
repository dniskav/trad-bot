import os
import json
import urllib.request
from typing import Optional
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))

from shared.persistence import JsonStore
from shared.logger import get_logger
from shared.settings import env_str
import aiohttp

log = get_logger("stm.account_service")
SYMBOL = env_str("SERVER_SYMBOL", "dogeusdt").lower()

# Persistencia para cuenta sintética
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORE = JsonStore(DATA_DIR)
ACCOUNT_FILE = "account_synth"
_last_price: Optional[float] = None


class AccountService:
    def __init__(self):
        self.store = STORE
        self.account_file = ACCOUNT_FILE

    def _fetch_price_rest(self, symbol: str) -> Optional[float]:
        """Fetch current price from Binance REST API"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return float(data.get("price"))
        except Exception:
            return None

    def _compute_balances(self, payload: dict) -> dict:
        """Compute current_balance and total_balance_usdt"""
        price = float(payload.get("doge_price", 0) or 0)
        usdt_balance = float(payload.get("usdt_balance", 0) or 0)
        doge_balance = float(payload.get("doge_balance", 0) or 0)
        usdt_locked = float(payload.get("usdt_locked", 0) or 0)
        doge_locked = float(payload.get("doge_locked", 0) or 0)

        # Total balance includes both available and locked funds
        # (locked funds are still part of the account, just not available for trading)
        total_balance = (
            usdt_balance + doge_balance * price + usdt_locked + doge_locked * price
        )

        # Current balance is only the available funds (excluding locked)
        current_balance = usdt_balance + doge_balance * price

        payload["current_balance"] = current_balance
        payload["total_balance_usdt"] = total_balance
        return payload

    async def ensure_account_initialized(self) -> None:
        """Initialize account with default values if not exists"""
        data = self.store.read(self.account_file, None)
        if data is None:
            price = _last_price or self._fetch_price_rest("dogeusdt") or 0.0
            # 500 USDT y 500 equivalentes en DOGE
            doge_balance = (500.0 / price) if price > 0 else 0.0
            data = {
                "initial_balance": 1000.0,
                "current_balance": 1000.0,
                "total_pnl": 0.0,
                "usdt_balance": 500.0,
                "doge_balance": doge_balance,
                "usdt_locked": 0.0,
                "doge_locked": 0.0,
                "doge_price": price,
                "total_balance_usdt": 1000.0,
                "invested": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
            data = self._compute_balances(data)
            self.store.write(self.account_file, data)

    async def get_account(self) -> dict:
        """Get current synthetic account data"""
        data = self.store.read(self.account_file, None)
        if data is None:
            await self.ensure_account_initialized()
            data = self.store.read(self.account_file, {})
        return data

    async def reset_account(self) -> dict:
        """Reset account to default values"""
        price = _last_price or self._fetch_price_rest(SYMBOL) or 0.0
        doge_balance = (500.0 / price) if price > 0 else 0.0
        data = {
            "initial_balance": 1000.0,
            "current_balance": 1000.0,
            "total_pnl": 0.0,
            "usdt_balance": 500.0,
            "doge_balance": doge_balance,
            "usdt_locked": 0.0,
            "doge_locked": 0.0,
            "doge_price": price,
            "total_balance_usdt": 1000.0,
            "invested": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        data = self._compute_balances(data)
        self.store.write(self.account_file, data)
        # Notify main server about balance update
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"type": "account_balance_update", "data": data}
                await session.post("http://localhost:8200/ws/notify", json=payload)
        except Exception:
            # Non-blocking notify
            pass
        return {"status": "ok", "data": data}


def update_price(price: float) -> None:
    """Update the last known price (called from Binance service)"""
    global _last_price
    _last_price = price
