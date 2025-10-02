#!/usr/bin/env python3
"""
Account Domain Model
Modelo de dominio para cuentas y gestión de balances
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
from .position import Money

from enum import Enum


class AssetType(Enum):
    """Tipos de activo"""

    USDT = "USDT"
    DOGE = "DOGE"
    BTC = "BTC"
    ETH = "ETH"


class TransactionType(Enum):
    """Tipos de transacción"""

    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    COMMISSION = "COMMISSION"
    FUNDING_FEE = "FUNDING_FEE"
    TRADE_PNL = "TRADE_PNL"
    POSITION_OPEN = "POSITION_OPEN"
    POSITION_CLOSE = "POSITION_CLOSE"
    BALANCE_UPDATE = "BALANCE_UPDATE"


@dataclass
class AssetBalance:
    """Balance de un activo específico"""

    asset: AssetType
    free: Money  # Disponible para trading
    locked: Money  # Bloqueado en órdenes/posiciones
    borrowed: Money = field(default_factory=lambda: Money.zero("USDT"))
    interest: Money = field(default_factory=lambda: Money.zero("USDT"))

    def __post_init__(self):
        """Validar balances después de inicializar"""
        if isinstance(self.free, (int, float)):
            self.free = Money.from_float(self.free)
        if isinstance(self.locked, (int, float)):
            self.locked = Money.from_float(self.locked)

    def get_total_amount(self) -> Money:
        """Obtener cantidad total (free + locked)"""
        return self.free + self.locked

    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        return {
            "asset": self.asset.value,
            "free": str(self.free.amount),
            "locked": str(self.locked.amount),
            "borrowed": str(self.borrowed.amount),
            "interest": str(self.interest.amount),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AssetBalance":
        """Crear desde diccionario"""
        asset = AssetType(data["asset"])
        free = Money.from_float(float(data["free"]))
        locked = Money.from_float(float(data["locked"]))
        borrowed = Money.from_float(float(data.get("borrowed", 0)))
        interest = Money.from_float(float(data.get("interest", 0)))
        return cls(asset, free, locked, borrowed, interest)


@dataclass
class BalanceChange:
    """Cambio en balance"""

    asset: AssetType
    amount: Decimal
    transaction_type: TransactionType
    description: str
    related_position_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convertir a diccionario"""
        return {
            "asset": self.asset.value,
            "amount": str(self.amount),
            "transaction_type": self.transaction_type.value,
            "description": self.description,
            "related_position_id": self.related_position_id,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BalanceChange":
        """Crear desde diccionario"""
        return cls(
            asset=AssetType(data["asset"]),
            amount=Decimal(data["amount"]),
            transaction_type=TransactionType(data["transaction_type"]),
            description=data["description"],
            related_position_id=data.get("related_position_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class AccountAggregate:
    """Agregado de dominio para Account"""

    account_id: str = "default"
    assets: List[AssetBalance] = field(default_factory=list)
    initial_balance_usdt: Money = field(default_factory=lambda: Money.zero("USDT"))
    total_balance_usdt: Money = field(default_factory=lambda: Money.zero("USDT"))
    current_balance_usdt: Money = field(default_factory=lambda: Money.zero("USDT"))
    total_pnl: Money = field(default_factory=lambda: Money.zero("USDT"))
    invested_amount: Money = field(default_factory=lambda: Money.zero("USDT"))

    # Metadatos
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_asset(
        self, asset: AssetType, free_amount: Money, locked_amount: Money = None
    ) -> None:
        """Agregar activo a la cuenta"""
        if locked_amount is None:
            locked_amount = Money.zero(asset.value)

        # Verificar si ya existe este activo
        for existing_asset in self.assets:
            if existing_asset.asset == asset:
                existing_asset.free = existing_asset.free + free_amount
                existing_asset.locked = existing_asset.locked + locked_amount
                self.updated_at = datetime.now()
                return

        # Crear nuevo activo si no existe
        new_asset = AssetBalance(asset, free_amount, locked_amount)
        self.assets.append(new_asset)
        self.updated_at = datetime.now()

    def get_asset_balance(self, asset: AssetType) -> Optional[AssetBalance]:
        """Obtener balance de un activo específico"""
        for balance in self.assets:
            if balance.asset == asset:
                return balance
        return None

    def lock_funds(self, asset: AssetType, amount: Money) -> bool:
        """Bloquear fondos para trading"""
        asset_balance = self.get_asset_balance(asset)
        if not asset_balance:
            return False

        if asset_balance.free.amount < amount.amount:
            return False  # Fondos insuficientes

        asset_balance.free = asset_balance.free - amount
        asset_balance.locked = asset_balance.locked + amount
        self.updated_at = datetime.now()
        self.last_activity = datetime.now()
        return True

    def unlock_funds(self, asset: AssetType, amount: Money) -> bool:
        """Desbloquear fondos"""
        asset_balance = self.get_asset_balance(asset)
        if not asset_balance:
            return False

        if asset_balance.locked.amount < amount.amount:
            return False  # Fondos bloqueados insuficientes

        asset_balance.locked = asset_balance.locked - amount
        asset_balance.free = asset_balance.free + amount
        self.updated_at = datetime.now()
        self.last_activity = datetime.now()
        return True

    def update_pnl(self, pnl_change: Money) -> None:
        """Actualizar P&L total"""
        self.total_pnl = self.total_pnl + pnl_change
        self.updated_at = datetime.now()
        self.last_activity = datetime.now()

    def calculate_total_value_usdt(self, prices: Dict[AssetType, Money]) -> Money:
        """Calcular valor total en USDT usando precios proporcionados"""
        total_value = Money.zero("USDT")

        for asset_balance in self.assets:
            # Obtener precio en USDT para este activo
            price = prices.get(asset_balance.asset, Money.zero("USDT"))
            # Solo considerar activos que tienen precio
            if price.amount > 0:
                asset_total = asset_balance.get_total_amount().amount * price.amount
                total_value = total_value + Money(
                    Decimal(str(price.amount)) * asset_total, "USDT"
                )

        return total_value

    def has_sufficient_balance(self, asset: AssetType, required_amount: Money) -> bool:
        """Verificar si hay balance suficiente"""
        asset_balance = self.get_asset_balance(asset)
        if not asset_balance:
            return False

        return asset_balance.free.amount >= required_amount.amount

    def get_account_summary(self) -> Dict:
        """Obtener resumen de la cuenta"""
        return {
            "account_id": self.account_id,
            "total_balance_usdt": str(self.total_balance_usdt.amount),
            "current_balance_usdt": str(self.current_balance_usdt.amount),
            "initial_balance_usdt": str(self.initial_balance_usdt.amount),
            "total_pnl": str(self.total_pnl.amount),
            "invested_amount": str(self.invested_amount.amount),
            "pnl_percentage": (
                float(self.total_pnl.amount / self.initial_balance_usdt.amount * 100)
                if self.initial_balance_usdt.amount > 0
                else 0.0
            ),
            "asset_count": len(self.assets),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    def to_dict(self) -> Dict:
        """Convertir a diccionario para persistencia"""
        return {
            "account_id": self.account_id,
            "assets": [asset.to_dict() for asset in self.assets],
            "initial_balance_usdt": str(self.initial_balance_usdt.amount),
            "total_balance_usdt": str(self.total_balance_usdt.amount),
            "current_balance_usdt": str(self.current_balance_usdt.amount),
            "total_pnl": str(self.total_pnl.amount),
            "invested_amount": str(self.invested_amount.amount),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AccountAggregate":
        """Crear desde diccionario de persistencia"""
        assets = [
            Assetbalance.from_dict(asset_data) for asset_data in data.get("assets", [])
        ]

        return cls(
            account_id=data.get("account_id", "default"),
            assets=assets,
            initial_balance_usdt=Money.from_float(
                float(data.get("initial_balance_usdt", 0))
            ),
            total_balance_usdt=Money.from_float(
                float(data.get("total_balance_usdt", 0))
            ),
            current_balance_usdt=Money.from_float(
                float(data.get("current_balance_usdt", 0))
            ),
            total_pnl=Money.from_float(float(data.get("total_pnl", 0))),
            invested_amount=Money.from_float(float(data.get("invested_amount", 0))),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat())
            ),
            last_activity=datetime.fromisoformat(
                data.get("last_activity", datetime.now().isoformat())
            ),
        )

    @classmethod
    def create_default(cls) -> "AccountAggregate":
        """Crear cuenta con valores por defecto"""
        account = cls()

        # Agregar balances iniciales (500 USDT + 500 equivalente en DOGE)
        account.add_asset(AssetType.USDT, Money.from_float(500.0))
        account.add_asset(
            AssetType.DOGE, Money.from_float(5000.0)
        )  # Aproximadamente 500 USDT a DOGE precio 0.10

        account.initial_balance_usdt = Money.from_float(1000.0)
        account.total_balance_usdt = Money.from_float(1000.0)
        account.current_balance_usdt = Money.from_float(1000.0)

        return account
