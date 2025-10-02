#!/usr/bin/env python3
"""
Account Domain Ports
Interfaces para el dominio de cuentas
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
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


@dataclass
class AssetBalance:
    """Balance de un activo específico"""
    asset: AssetType
    free: float  # Disponible para trading
    locked: float  # Bloqueado en órdenes/posiciones
    borrowed: float = 0.0  # Pedido prestado
    interest: float = 0.0  # Interés acumulado


@dataclass
class Account:
    """Modelo de cuenta completa"""
    account_id: str
    total_balance_usdt: float
    current_balance_usdt: float
    initial_balance_usdt: float
    total_pnl: float
    assets: List[AssetBalance]
    
    # Metadatos
    created_at: str
    updated_at: str
    last_activity: str


@dataclass
class BalanceChange:
    """Cambio en balance"""
    asset: AssetType
    amount: float
    transaction_type: TransactionType
    description: str
    related_position_id: Optional[str] = None
    timestamp: str = datetime.now().isoformat()


class IAccountRepository(ABC):
    """Repositorio para gestión de cuentas"""

    @abstractmethod
    async def get_account(self, account_id: str = "default") -> Optional[Account]:
        """Obtener cuenta por ID"""
        pass

    @abstractmethod
    async def save_account(self, account: Account) -> None:
        """Guardar cuenta"""
        pass

    @abstractmethod
    async def update_account_balance(self, account_id: str, balance_change: BalanceChange) -> Account:
        """Actualizar balance de cuenta"""
        pass

    @abstractmethod
    async def get_account_history(self, account_id: str, limit: int = 100) -> List[BalanceChange]:
        """Obtener historial la cuenta"""
        pass


class IBalanceCalculator(ABC):
    """Calculadora de balances y P&L"""

    @abstractmethod
    def calculate_account_total_usdt(self, assets: List[AssetBalance], prices: Dict[AssetType, float]) -> float:
        """Calcular balance total en USDT"""
        pass

    @abstractmethod
    def calculate_current_balance_usdt(self, assets: List[AssetBalance], prices: Dict[AssetType, float]) -> float:
        """Calcular balance disponible en USDT"""
        pass

    @abstractmethod
    def calculate_total_pnl(self, initial_balance: float, current_total: float) -> float:
        """Calcular P&L total"""
        pass

    @abstractmethod
    def calculate_margin_required(self, position_size: float, leverage: int) -> float:
        """Calcular margen requerido"""
        pass

    @abstractmethod
    def calculate_margin_available(self, account: Account, symbols_to_query: List[str]) -> float:
        """Calcular margen disponible"""
        pass


class ICommissionCalculator(ABC):
    """Calculadora de comisiones"""

    @abstractmethod
    def calculate_trade_commission(self, asset: AssetType, quantity: float, price: float, is_maker: bool = False) -> float:
        """Calcular comisión de trade"""
        pass

    @abstractmethod
    def calculate_funding_fee(self, position_size: float, price: float, hours: int = 8) -> float:
        """Calcular funding fee"""
        pass

    @abstractmethod
    def calculate_borrow_fee(self, asset: AssetType, amount: float, days: int = 1) -> float:
        """Calcular fee de préstamo"""
        pass

    @abstractmethod
    def calculate_liquidation_fee(self, liquidated_amount: float) -> float:
        """Calcular fee de liquidación"""
        pass


class IAccountValidator(ABC):
    """Validador de operaciones de cuenta"""

    @abstractmethod
    async def validate_deposit_amount(self, asset: AssetType, amount: float) -> bool:
        """Validar cantidad de depósito"""
        pass

    @abstractmethod
    async def validate_withdrawal_amount(self, account: Account, asset: AssetType, amount: float) -> bool:
        """Validar cantidad de retiro"""
        pass

    @abstractmethod
    async def validate_position_margin(self, account: Account, required_margin: float, symbol: str) -> bool:
        """Validar margen disponible para posición"""
        pass

    @abstractmethod
    async def validate_balance_sufficiency(self, account: Account, required_amount: float, asset: AssetType) -> bool:
        """Validar suficientey de balance"""
        pass


class IAccountTransactionHandler(ABC):
    """Manejador de transacciones de cuenta"""

    @abstractmethod
    async def process_deposit(self, account_id: str, asset: AssetType, amount: float) -> BalanceChange:
        """Procesar depósito"""
        pass

    @abstractmethod
    async def process_withdrawal(self, account_id: str, asset: AssetType, amount: float) -> BalanceChange:
        """Procesar retiro"""
        pass

    @abstractmethod
    async def process_position_open_cost(self, account_id: str, symbol: str, margin_required: float, commission: float) -> List[BalanceChange]:
        """Procesar costo de apertura de posición"""
        pass

    @abstractmethod
    async def process_position_close_profit(self, account_id: str, symbol: str, pnl: float, commission: float) -> List[BalanceChange]:
        """Procesar profit/loss de cierre de posición"""
        pass

    @abstractmethod
    async def process_funding_fee(self, account_id: str, symbol: str, fee_amount: float) -> BalanceChange:
        """Procesar funding fee"""
        pass


class IAccountReportGenerator(ABC):
    """Generador de reportes de cuentas"""

    @abstractmethod
    async def generate_account_summary(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        """Generar resumen de cuenta"""
        pass

    @abstractmethod
    async def generate_pnl_report(self, account_id: str, period: str = "daily") -> Dict[str, Any]:
        """Generar reporte de P&L"""
        pass

    @abstractmethod
    async def generate_commission_report(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        """Generar reporte de comisiones"""
        pass

    @abstractmethod
    async def generate_asset_allocation_report(self, account_id: str) -> Dict[str, Any]:
        """Generar reporte de allocación de activos"""
        pass


class IMarketDataPricer(ABC):
    """Obtains current market prices for assets"""

    @abstractmethod
    async def get_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Obtener precios actuales de símbolos"""
        pass

    @abstractmethod
    async def get_price_in_usdt(self, asset: AssetType) -> float:
        """Obtener precio de activo en USDT"""
        pass

    @abstractmethod
    async def calculate_portfolio_value_usdt(self, assets: List[AssetBalance]) -> float:
        """Calcular valor de portafolio en USDT"""
        pass
