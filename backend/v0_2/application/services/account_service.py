#!/usr/bin/env python3
"""
Account Application Service
Servicio de aplicación para gestión de cuentas y balances
"""

from typing import Dict, List, Optional
from decimal import Decimal

from ...domain.models.account import (
    AccountAggregate,
    AssetBalance,
    AssetType,
    BalanceChange,
    TransactionType,
)
from ...domain.models.position import Money
from ...domain.ports.account_ports import (
    IAccountRepository,
    IBalanceCalculator,
    IAccountCommissionCalculator,
    IAccountValidator,
    IAccountTransactionHandler,
    IMarketDataPricer,
)
from ...domain.ports.communication_ports import IEventPublisher


class AccountApplicationService:
    """Servicio de aplicación para Account Domain"""

    def __init__(
        self,
        account_repository: IAccountRepository,
        balance_calculator: IBalanceCalculator,
        commission_calculator: IAccountCommissionCalculator,
        account_validator: IAccountValidator,
        transaction_handler: IAccountTransactionHandler,
        market_data_pricer: IMarketDataPricer,
        event_publisher: IEventPublisher,
    ):
        self.account_repository = account_repository
        self.balance_calculator = balance_calculator
        self.commission_calculator = commission_calculator
        self.account_validator = account_validator
        self.transaction_handler = transaction_handler
        self.market_data_pricer = market_data_pricer
        self.event_publisher = event_publisher

    async def get_account(
        self, account_id: str = "default"
    ) -> Optional[AccountAggregate]:
        """Obtener información de cuenta"""
        return await self.account_repository.get_account(account_id)

    async def ensure_account_exists(
        self, account_id: str = "default"
    ) -> AccountAggregate:
        """Asegurar que la cuenta existe, crearla si no"""
        account = await self.account_repository.get_account(account_id)

        if not account:
            # Crear cuenta con valores por defecto
            account = AccountAggregate.create_default()
            account.account_id = account_id

            # Calcular balances usando precios actuales
            await self.update_account_pricing(account)

            # Guardar cuenta nueva
            await self.account_repository.save_account(account)

            # Publicar evento de cuenta creada
            await self.event_publisher.publish_account_event(
                account_id,
                "account_created",
                {"balance_usdt": str(account.total_balance_usdt.amount)},
            )

        return account

    async def update_account_pricing(self, account: AccountAggregate) -> None:
        """Actualizar precios y calcular balances en USDT"""

        # Obtener precios actuales de market data
        usdt_price = Money.from_float(1.0)  # USDT siempre es 1:1

        prices = {AssetType.USDT: usdt_price}

        # Obtener precio de DOGE si existe en la cuenta
        doge_balance = account.get_asset_balance(AssetType.DOGE)
        if doge_balance:
            try:
                doge_price_usdt = await self.market_data_pricer.get_price_usdt(
                    "DOGEUSDT"
                )
                prices[AssetType.DOGE] = Money.from_float(doge_price_usdt)
            except Exception:
                # Si hay error, usar precio por defecto
                prices[AssetType.DOGE] = Money.from_float(0.085)

        # Calcular balances usando BalanceCalculator
        total_balance, current_balance = (
            await self.balance_calculator.calculate_balances(account, prices)
        )

        # Actualizar balances en la cuenta
        account.total_balance_usdt = total_balance
        account.current_balance_usdt = current_balance

        # Publicar evento de actualización de balance
        await self.event_publisher.publish_account_event(
            account.account_id,
            "balance_updated",
            {
                "total_balance_usdt": str(total_balance.amount),
                "current_balance_usdt": str(current_balance.amount),
            },
        )

    async def process_trade_transaction(
        self,
        account_id: str,
        asset: AssetType,
        amount: Money,
        transaction_type: TransactionType,
        position_id: Optional[str] = None,
        description: str = "",
    ) -> bool:
        """Procesar transacción de trading"""

        account = await self.ensure_account_exists(account_id)

        # Validar transacción
        is_valid = await self.account_validator.validate_transaction(
            account, asset, amount, transaction_type
        )

        if not is_valid:
            return False

        # Crear balance change record
        balance_change = BalanceChange(
            asset=asset,
            amount=amount.amount,
            transaction_type=transaction_type,
            description=description,
            related_position_id=position_id,
        )

        # Procesar transacción usando TransactionHandler
        processed_account = await self.transaction_handler.process_transaction(
            account, balance_change
        )

        if processed_account:
            # Actualizar cuentas con nuevos balances
            await self.update_account_balances(processed_account)

            # Guardar cambios
            await self.account_repository.save_account(processed_account)

            # Publicar evento de transacción
            await self.event_publisher.publish_account_event(
                account_id,
                "transaction_processed",
                {
                    "asset": asset.value,
                    "amount": str(amount.amount),
                    "transaction_type": transaction_type.value,
                    "position_id": position_id,
                },
            )

            return True

        return False

    async def lock_funds_for_position(
        self, account_id: str, asset: AssetType, amount: Money, position_id: str
    ) -> bool:
        """Bloquear fondos para nueva posición"""

        account = await self.ensure_account_exists(account_id)

        # Verificar que tiene fondos suficientes
        if not account.has_sufficient_balance(asset, amount):
            return False

        # Validar bloqueo
        is_valid = await self.account_validator.can_lock_funds(account, asset, amount)
        if not is_valid:
            return False

        # Bloquear fondos
        success = account.lock_funds(asset, amount)

        if success:
            # Crear transacción de bloqueo
            from ...domain.models.account import BalanceChange, TransactionType

            balance_change = BalanceChange(
                asset=asset,
                amount=-amount.amount,  # Negativo porque se reduce el libre
                transaction_type=TransactionType.POSITION_OPEN,
                description=f"Funds locked for position {position_id}",
                related_position_id=position_id,
            )

            # Guardar cambio de balance
            await self.account_repository.add_balance_change(account_id, balance_change)

            # Guardar cuenta actualizada
            await self.account_repository.save_account(account)

            # Publicar evento
            await self.event_publisher.publish_account_event(
                account_id,
                "funds_locked",
                {
                    "asset": asset.value,
                    "amount": str(amount.amount),
                    "position_id": position_id,
                },
            )

            return True

        return False

    async def unlock_funds_from_position(
        self, account_id: str, asset: AssetType, amount: Money, position_id: str
    ) -> bool:
        """Desbloquear fondos de posición cerrada"""

        account = await self.ensure_account_exists(account_id)

        # Desbloquear fondos
        success = account.unlock_funds(asset, amount)

        if success:
            # Crear transacción de desbloqueo
            balance_change = BalanceChange(
                asset=asset,
                amount=amount.amount,  # Positivo porque se incrementa el libre
                transaction_type=TransactionType.POSITION_CLOSE,
                description=f"Funds unlocked from position {position_id}",
                related_position_id=position_id,
            )

            # Guardar cambio de balance
            await self.account_repository.add_balance_change(account_id, balance_change)

            # Guardar cuenta actualizada
            await self.account_repository.save_account(account)

            # Publicar evento
            await self.event_publisher.publish_account_event(
                account_id,
                "funds_unlocked",
                {
                    "asset": asset.value,
                    "amount": str(amount.amount),
                    "position_id": position_id,
                },
            )

            return True

        return False

    async def calculate_commission(
        self,
        trade_value: Money,
        asset: AssetType,
        commission_rate: Optional[Decimal] = None,
    ) -> Money:
        """Calcular comisión para una operación"""

        return await self.commission_calculator.calculate_commission(
            trade_value, asset, commission_rate
        )

    async def process_commission_payment(
        self,
        account_id: str,
        commission_amount: Money,
        asset: AssetType,
        position_id: Optional[str] = None,
    ) -> bool:
        """Procesar pago de comisión"""

        success = await self.process_trade_transaction(
            account_id=account_id,
            asset=asset,
            amount=commission_amount,
            transaction_type=TransactionType.COMMISSION,
            position_id=position_id,
            description=f"Commission payment: {commission_amount.amount}",
        )

        if success:
            await self.event_publisher.publish_account_event(
                account_id,
                "commission_paid",
                {
                    "asset": asset.value,
                    "commission_amount": str(commission_amount.amount),
                    "position_id": position_id,
                },
            )

        return success

    async def update_account_balances(self, account: AccountAggregate) -> None:
        """Actualizar balances calculados de una cuenta"""

        # Obtener precios actuales
        usdt_price = Money.from_float(1.0)
        prices = {AssetType.USDT: usdt_price}

        # Agregar otros precios según los assets de la cuenta
        for asset_balance in account.assets:
            if asset_balance.asset != AssetType.USDT:
                try:
                    symbol = f"{asset_balance.asset.value}USDT"
                    price_usdt = await self.market_data_pricer.get_price_usdt(symbol)
                    prices[asset_balance.asset] = Money.from_float(price_usdt)
                except Exception:
                    # Precio por defecto si hay error
                    default_prices = {
                        AssetType.DOGE: Money.from_float(0.085),
                        AssetType.BTC: Money.from_float(45000.0),
                        AssetType.ETH: Money.from_float(2500.0),
                    }
                    prices[asset_balance.asset] = default_prices.get(
                        asset_balance.asset, Money.from_float(1.0)
                    )

        # Calcular balances actualizados
        total_balance, current_balance = (
            await self.balance_calculator.calculate_balances(account, prices)
        )

        # Actualizar en la cuenta
        account.total_balance_usdt = total_balance
        account.current_balance_usdt = current_balance

    async def get_account_summary(self, account_id: str = "default") -> Dict:
        """Obtener resumen completo de la cuenta"""

        account = await self.ensure_account_exists(account_id)

        # Actualizar pricing antes de obtener resumen
        await self.update_account_pricing(account)

        return account.get_account_summary()

    async def reset_account(self, account_id: str = "default") -> Dict:
        """Resetear cuenta a valores por defecto"""

        # Crear nueva cuenta con valores por defecto
        new_account = AccountAggregate.create_default()
        new_account.account_id = account_id

        # Guardar cuenta reiniciada
        await self.account_repository.save_account(new_account)

        # Publicar evento de reset
        await self.event_publisher.publish_account_event(
            account_id,
            "account_reset",
            {"initial_balance": str(new_account.initial_balance_usdt.amount)},
        )

        return new_account.get_account_summary()
