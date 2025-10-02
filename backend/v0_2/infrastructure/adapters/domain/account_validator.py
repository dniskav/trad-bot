#!/usr/bin/env python3
"""
Account Validator Implementation
Implementación de IAccountValidator para validaciones de cuentas
"""

from typing import List
from decimal import Decimal

from ...domain.models.account import AccountAggregate, AssetType, TransactionType
from ...domain.models.position import Money
from ...domain.ports.account_ports import IAccountValidator


class StandardAccountValidator:
    """Validador estándar de cuentas"""

    def __init__(self):
        # Balances mínimos por asset
        self.minimum_balances = {
            AssetType.USDT: Money.from_float(0.01),
            AssetType.DOGE: Money.from_float(1.0),
            AssetType.BTC: Money.from_float(0.000001),
            AssetType.ETH: Money.from_float(0.0001),
        }

        # Límites de transacción por defecto
        self.transaction_limits = {
            TransactionType.DEPOSIT: Money.from_float(10000.0),  # Máximo $10k depósito
            TransactionType.WITHDRAWAL: Money.from_float(
                5000.0
            ),  # Máximo $5k withdrawal
            TransactionType.COMMISSION: Money.from_float(100.0),  # Máximo $100 comisión
            TransactionType.TRADE_PNL: Money.from_float(
                1000.0
            ),  # Máximo $1k P&L por trade
            TransactionType.POSITION_OPEN: Money.from_float(
                2000.0
            ),  # Máximo $2k posición
            TransactionType.POSITION_CLOSE: Money.from_float(2000.0),
            TransactionType.FUNDING_FEE: Money.from_float(10.0),  # Máximo $10 funding
            TransactionType.BALANCE_UPDATE: Money.from_float(10000.0),
        }

    async def validate_transaction(
        self,
        account: AccountAggregate,
        asset: AssetType,
        amount: Money,
        transaction_type: TransactionType,
    ) -> bool:
        """Validar una proposed transacción"""

        # Validación básica de amount
        if amount.amount <= 0:
            return False

        # Validar límites de transacción
        transaction_limit = self.transaction_limits.get(transaction_type)
        if transaction_limit and amount.amount > transaction_limit.amount:
            return False

        # Validaciones específicas por tipo de transacción
        if transaction_type == TransactionType.WITHDRAWAL:
            return await self._validate_withdrawal(account, asset, amount)

        elif transaction_type == TransactionType.POSITION_OPEN:
            return await self._validate_position_open(account, asset, amount)

        elif transaction_type == TransactionType.COMMISSION:
            return await self._validate_commission(account, asset, amount)

        elif transaction_type == TransactionType.DEPOSIT:
            return True  # Los depósitos generalmente están permitidos

        else:
            return True  # Otros tipos por defecto permitidos

    async def _validate_withdrawal(
        self, account: AccountAggregate, asset: AssetType, amount: Money
    ) -> bool:
        """Validar withdrawal"""

        # Obtener balance del asset
        asset_balance = account.get_asset_balance(asset)
        if not asset_balance:
            return False  # Asset no existe en la cuenta

        # Verificar que hay fondos suficientes
        if asset_balance.free.amount < amount.amount:
            return False

        return True

    async def _validate_position_open(
        self, account: AccountAggregate, asset: AssetType, amount: Money
    ) -> bool:
        """Validar apertura de posición"""

        # Verificar que hay fondos libres suficientes
        return await self.can_lock_funds(account, asset, amount)

    async def _validate_commission(
        self, account: AccountAggregate, asset: AssetType, amount: Money
    ) -> bool:
        """Validar pago de comisión"""

        # Las comisiones generalmente se pueden pagar con cualquier asset disponible
        asset_balance = account.get_asset_balance(asset)
        return asset_balance is not None and asset_balance.free.amount >= amount.amount

    async def can_lock_funds(
        self, account: AccountAggregate, asset: AssetType, amount: Money
    ) -> bool:
        """Verificar si se pueden bloquear fondos"""

        asset_balance = account.get_asset_balance(asset)
        if not asset_balance:
            return False

        # Verificar balance disponible
        return asset_balance.free.amount >= amount.amount

    async def can_unlock_funds(
        self, account: AccountAggregate, asset: AssetType, amount: Money
    ) -> bool:
        """Verificar si se pueden desbloquear fondos"""

        asset_balance = account.get_asset_balance(asset)
        if not asset_balance:
            return False

        # Verificar balance bloqueado
        return asset_balance.locked.amount >= amount.amount

    async def validate_account_balance_integrity(
        self, account: AccountAggregate
    ) -> List[str]:
        """Validar integridad de balances de la cuenta"""

        errors = []

        # Verificar que cada asset tiene balance positivo
        for asset_balance in account.assets:
            if asset_balance.free.amount < 0:
                errors.append(f"Negative free balance: {asset_balance.asset.value}")

            if asset_balance.locked.amount < 0:
                errors.append(f"Negative locked balance: {asset_balance.asset.value}")

        # Verificar integridad de totales USDT
        if account.total_balance_usdt.amount < 0:
            errors.append("Negative total balance USDT")

        if account.current_balance_usdt.amount < 0:
            errors.append("Negative current balance USDT")

        if account.initial_balance_usdt.amount < 0:
            errors.append("Negative initial balance USDT")

        # Verificar que current <= total (current excludes locked)
        if account.current_balance_usdt.amount > account.total_balance_usdt.amount:
            errors.append("Current balance exceeds total balance")

        return errors

    async def validate_account_activity(self, account: AccountAggregate) -> bool:
        """Validar actividad reciente de la cuenta"""

        from datetime import datetime, timedelta

        # Verificar que la cuenta ha sido actualizada recientemente
        # (máximo 7 días sin actividad)
        max_inactivity_days = 7
        cutoff_date = datetime.now() - timedelta(days=max_inactivity_days)

        if account.last_activity < cutoff_date:
            return False  # Cuenta inactiva

        return True

    async def validate_trading_limits(
        self, account: AccountAggregate, daily_volume: Money = None
    ) -> bool:
        """Validar límites de trading"""

        # Límite diario por defecto: $5,000 USDT
        daily_limit = Money.from_float(5000.0)

        if daily_volume and daily_volume.amount > daily_limit.amount:
            return False  # Excede límite diario

        # Verificar que la cuenta tiene balance mínimo para trading
        usdt_balance = account.get_asset_balance(AssetType.USDT)
        if usdt_balance:
            min_trading_balance = Money.from_float(10.0)  # Mínimo $10 para trading
            return usdt_balance.free.amount >= min_trading_balance.amount

        return False


class AdvancedAccountValidator(StandardAccountValidator):
    """Validador avanzado con reglas más sofisticadas"""

    def __init__(self):
        super().__init__()

        # Límites por VIP level
        self.vip_limits = {
            0: {
                "daily": Money.from_float(5000.0),
                "monthly": Money.from_float(100000.0),
            },
            1: {
                "daily": Money.from_float(10000.0),
                "monthly": Money.from_float(250000.0),
            },
            2: {
                "daily": Money.from_float(50000.0),
                "monthly": Money.from_float(500000.0),
            },
            3: {
                "daily": Money.from_float(100000.0),
                "monthly": Money.from_float(1000000.0),
            },
            4: {
                "daily": Money.from_float(250000.0),
                "monthly": Money.from_float(2000000.0),
            },
        }

    async def validate_vip_transaction(
        self,
        account: AccountAggregate,
        asset: AssetType,
        amount: Money,
        transaction_type: TransactionType,
        vip_level: int = 0,
        daily_volume: Money = None,
    ) -> bool:
        """Validar transacción con límites VIP"""

        # Verificar límites VIP
        vip_limit = self.vip_limits.get(vip_level, self.vip_limits[0])
        daily_limit = vip_limit["daily"]
        monthly_limit = vip_limit["monthly"]

        if daily_volume:
            if daily_volume.amount > daily_limit.amount:
                return False

        # Validación específica VIP según tipo de transacción
        vip_multiplier = {
            TransactionType.DEPOSIT: Decimal("5.0"),  # VIP deposita hasta 5x más
            TransactionType.WITHDRAWAL: Decimal("3.0"),  # VIP retira hasta 3x más
            TransactionType.POSITION_OPEN: Decimal(
                "2.0"
            ),  # VIP posiciones 2x más grandes
            TransactionType.COMMISSION: Decimal(
                "10.0"
            ),  # VIP puede pagar comisiones más altas
        }

        multiplier = vip_multiplier.get(transaction_type, Decimal("1.0"))
        adjusted_limit = Money(
            self.transaction_limits.get(transaction_type, Money.zero("USDT")).amount
            * multiplier,
            "USDT",
        )

        return amount.amount <= adjusted_limit.amount

    async def validate_risk_management(
        self, account: AccountAggregate, position_value: Money, leverage: int
    ) -> bool:
        """Validar gestión de riesgo para nuevas posiciones"""

        # Ratio de riesgo máximo: 20% del capital total
        max_risk_ratio = Decimal("0.20")

        # Calcular exposición total (incluyendo nueva posición)
        current_exposure = Decimal("0")

        # Sumar assets bloqueados en posiciones existentes
        for asset_balance in account.assets:
            # Convertir a USDT (usar conversiones aproximadas)
            if asset_balance.asset == AssetType.USDT:
                exposure_per_asset = asset_balance.locked.amount
            elif asset_balance.asset == AssetType.DOGE:
                exposure_per_asset = asset_balance.locked.amount * Decimal("0.085")
            elif asset_balance.asset == AssetType.BTC:
                exposure_per_asset = asset_balance.locked.amount * Decimal("45000")
            elif asset_balance.asset == AssetType.ETH:
                exposure_per_asset = asset_balance.locked.amount * Decimal("2500")
            else:
                exposure_per_asset = Decimal("0")

            current_exposure += exposure_per_asset

        # Sumar nueva posición
        total_exposure = current_exposure + position_value.amount

        # Calcular porcentaje del capital total
        if account.total_balance_usdt.amount > 0:
            risk_ratio = total_exposure / account.total_balance_usdt.amount

            if risk_ratio > max_risk_ratio:
                return False  # Excede límite de riesgo

        return True

    async def validate_knowledge_check(
        self, account: AccountAggregate, leverage: int, position_size_usdt: Money
    ) -> bool:
        """Validar que el trader entiende los riesgos (mock implementation)"""

        # Para posiciones grandes o alto leverage requerir "knowledge check"
        large_position_threshold = Money.from_float(1000.0)
        high_leverage_threshold = 5

        needs_knowledge_check = (
            position_size_usdt.amount > large_position_threshold.amount
            or leverage > high_leverage_threshold
        )

        if needs_knowledge_check:
            # En implementación real esto requeriría:
            # - Verificación de nivel educativo
            # - Test de conocimientos de trading
            # - Experiencia previa documentada

            # Por ahora retornamos True (trader competent)
            return True

        return True
