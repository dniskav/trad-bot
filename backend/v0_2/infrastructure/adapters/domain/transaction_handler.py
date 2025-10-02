#!/usr/bin/env python3
"""
Transaction Handler Implementation
Implementación de IAccountTransactionHandler para manejo de transacciones
"""

from copy import deepcopy
from typing import Optional

from ...domain.models.account import AccountAggregate, AssetType, TransactionType, BalanceChange
from ...domain.models.position import Money
from ...domain.ports.account_ports import IAccountTransactionHandler


class StandardTransactionHandler:
    """Manejador estándar de transacciones"""

    async def process_transaction(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> Optional[AccountAggregate]:
        """Procesar una transacción en la cuenta"""
        
        # Crear copia de la cuenta para modificarla
        updated_account = deepcopy(account)
        
        # Procesar según tipo de transacción
        transaction_type = balance_change.transaction_type
        
        if transaction_type == TransactionType.DEPOSIT:
            success = await self._process_deposit(updated_account, balance_change)
        elif transaction_type == TransactionType.WITHDRAWAL:
            success = await self._process_withdrawal(updated_account, balance_change)
        elif transaction_type == TransactionType.COMMISSION:
            success = await self._process_commission(updated_account, balance_change)
        elif transaction_type == TransactionType.FUNDING_FEE:
            success = await self._process_funding_fee(updated_account, balance_change)

        elif transaction_type == TransactionType.TRADE_PNL:
            success = await self._process_trade_pnl(updated_account, balance_change)
        elif transaction_type == TransactionType.POSITION_OPEN:
            success = await self._process_position_open(updated_account, balance_change)
        elif transaction_type == TransactionType.POSITION_CLOSE:
            success = await self._process_position_close(updated_account, balance_change)
        elif transaction_type == TransactionType.BALANCE_UPDATE:
            success = await self._process_balance_update(updated_account, balance_change)
        else:
            return None  # Tipo desconocido
        
        if success:
            return updated_account
        else:
            return None

    async def _process_deposit(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar depósito"""
        
        # Agregar fondos al balance libre del asset
        asset = balance_change.asset
        amount = Money(balance_change.amount, asset.value)
        
        current_balance = account.get_asset_balance(asset)
        if current_balance:
            # Actualizar balance existente
            current_balance.free = current_balance.free + amount
        else:
            # Crear nuevo asset balance
            account.add_asset(asset, amount, Money.zero(asset.value))
        
        # Actualizar metadatos
        account.last_activity = balance_change.timestamp
        
        return True

    async def _process_withdrawal(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar retiro"""
        
        # Remover fondos del balance libre del asset
        asset = balance_change.asset
        amount = Money(abs(balance_change.amount), asset.value)  # Hacer positivo
        
        current_balance = account.get_asset_balance(asset)
        if not current_balance:
            return False  # Asset no existe
        
        # Verificar que hay fondos suficientes
        if current_balance.free.amount < amount.amount:
            return False  # Fondos insuficientes
        
        # Reducir balance libre
        current_balance.free = current_balance.free - amount
        
        # Si queda balance negativo en free, mover a locked si es posible
        if current_balance.free.amount < Money.zero(asset.value).amount:
            # En realidad esto no debería pasar después de verificaciones
            current_balance.free = Money.zero(asset.value)
        
        # Actualizar metadatos
        account.last_activity = balance_change.timestamp
        
        return True

    async def _process_commission(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar pago de comisión"""
        
        # Comisiones se procesan como withdrawal
        return await self._process_withdrawal(account, balance_change)

    async def _process_funding_fee(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar funding fee"""
        
        # Funding fees se procesan como withdrawal
        return await self._process_withdrawal(account, balance_change)

    async def _process_trade_pnl(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar P&L de trade"""
        
        asset = balance_change.asset
        amount = Money(balance_change.amount, asset.value)
        
        if amount.amount > 0:
            # Ganancia: procesar como depósito
            return await self._process_deposit(account, balance_change)
        else:
            # Pérdida: procesar como retiro
            withdrawal_change = BalanceChange(
                asset=asset,
                amount=abs(amount.amount),  # Hacer positivo para withdrawal
                transaction_type=TransactionType.WITHDRAWAL,
                description=f"Trade loss: {balance_change.description}",
                related_position_id=balance_change.related_position_id,
                timestamp=balance_change.timestamp
            )
            return await self._process_withdrawal(account, withdrawal_change)

    async def _process_position_open(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """
        Procesar apertura de posición
        Cantidad negativa significa bloqueo de fondos
        """
        
        asset = balance_change.asset
        amount = Money(abs(balance_change.amount), asset.value)
        
        # Verificar que se pueden bloquear los fondos
        return account.lock_funds(asset, amount)

    async def _process_position_close(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """
        Procesar cierre de posición
        Cantidad positiva significa desbloqueo de fondos
        """
        
        asset = balance_change.asset
        amount = Money(balance_change.amount, asset.value)
        
        # Verificar que se pueden desbloquear los fondos
        return account.unlock_funds(asset, amount)

    async def _process_balance_update(
        self, 
        account: AccountAggregate, 
        balance_change: BalanceChange
    ) -> bool:
        """Procesar actualización de balance (reconciliación)"""
        
        # Para balance updates, podemos simplemente actualizar el metadata
        account.last_activity = balance_change.timestamp
        return True

    async def calculate_net_asset_value(
        self, 
        account: AccountAggregate,
        prices: dict[AssetType, Money]
    ) -> Money:
        """Calcular valor neto total de activos"""
        
        net_value = Money.zero("USDT")
        
        for asset_balance in account.assets:
            asset_type = asset_balance.asset
            
            # Obtener precio en USDT
            if asset_type == AssetType.USDT:
                price_usdt = Money.from_float(1.0)
            else:
                price_usdt = prices.get(asset_type, Money.from_float(1.0))
            
            # Calcular valor total del asset (free + locked)
            asset_total = asset_balance.get_total_amount()
            asset_value_usdt = Money(
                asset_total.amount * price_usdt.amount,
                "USDT"
            )
            
            net_value = net_value + asset_value_usdt
        
        return net_value

    async def reconcile_balance_discrepancies(
        self, 
        account: AccountAggregate,
        expected_balance_usdt: Money,
        tolerance: Money = None
    ) -> list[str]:
        """Reconciliar discrepancias en balances"""
        
        if tolerance is None:
            tolerance = Money.from_float(1.0)  # $1 tolerancia por defecto
        
        discrepancies = []
        
        # Calcular diferencia
        current_total = account.total_balance_usdt
        difference = Money(
            abs(current_total.amount - expected_balance_usdt.amount),
            "USDT"
        )
        
        if difference.amount > tolerance.amount:
            discrepancy_type = "positive" if current_total.amount > expected_balance_usdt.amount else "negative"
            discrepancies.append(
                f"Total balance discrepancy: {discrepancy_type} ${difference.amount:.2f}"
            )
        
        return discrepancies

    async def apply_corrective_transaction(
        self, 
        account: AccountAggregate,
        discrepancy_amount: Money,
        description: str = "Balance reconciliation"
    ) -> Optional[AccountAggregate]:
        """Aplicar transacción correctiva para reconciliar balance"""
        
        # Determinar tipo de transacción según el signo
        if discrepancy_amount.amount > 0:
            transaction_type = TransactionType.DEPOSIT
        else:
            transaction_type = TransactionType.WITHDRAWAL
        
        # Crear transacción correctiva
        corrective_transaction = BalanceChange(
            asset=AssetType.USDT,
            amount=abs(discrepancy_amount.amount),  # Guardar valor absoluto
            transaction_type=transaction_type,
            description=description,
            timestamp=account.last_activity
        )
        
        # Procesar transacción
        return await self.process_transaction(account, corrective_transaction)


class AdvancedTransactionHandler(StandardTransactionHandler):
    """Manejador avanzado de transacciones con características adicionales"""
    
    async def process_batch_transactions(
        self, 
        account: AccountAggregate, 
        transactions: list[BalanceChange]
    ) -> Optional[AccountAggregate]:
        """Procesar múltiples transacciones en batch"""
        
        updated_account = deepcopy(account)
        
        successful_transactions = []
        failed_transactions = []
        
        for transaction in transactions:
            # Crear cuenta temporal para esta transacción
            temp_account = deepcopy(updated_account)
            result = await self.process_transaction(temp_account, transaction)
            
            if result:
                # Transacción exitosa: actualizar cuenta
                updated_account = result
                successful_transactions.append(transaction)
                
                # Actualizar activity timestamp
                if transaction.timestamp > updated_account.last_activity:
                    updated_account.last_activity = transaction.timestamp
            else:
                # Transacción fallida
                failed_transactions.append(transaction)
        
        # Reportar estadísticas
        print(f"✅ Successful transactions: {len(successful_transactions)}")
        print(f"❌ Failed transactions: {len(failed_transactions)}")
        
        if successful_transactions:
            return updated_account
        else:
            return None

    async def detect_suspicious_transactions(
        self, 
        account: AccountAggregate, 
        transaction: BalanceChange
    ) -> list[str]:
        """Detectar transacciones sospechosas"""
        
        suspicious_indicators = []
        
        # Transaction size verification
        large_threshold = Money.from_float(1000.0)
        if abs(transaction.amount) > large_threshold.amount:
            suspicious_indicators.append(f"Large transaction detected: ${abs(transaction.amount):.2f}")
        
        # Frequency check (if we had access to transaction history)
        # This would require storing transaction frequencies
        
        # Unusual asset verification
        if transaction.asset not in [AssetType.USDT, AssetType.DOGE]:
            suspicious_indicators.append(f"Unusual asset transaction: {transaction.asset.value}")
        
        # Negative balance prevention
        asset_balance = account.get_asset_balance(transaction.asset)
        if asset_balance:
            after_transaction_free = asset_balance.free.amount - transaction.amount
            if after_transaction_free < 0:
                suspicious_indicators.append(f"Negative balance would result from this transaction")
        
        return suspicious_indicators

    async def generate_transaction_report(
        self, 
        account: AccountAggregate,
        transactions: list[BalanceChange]
    ) -> dict:
        """Generar reporte de transacciones"""
        
        report = {
            "total_transactions": len(transactions),
            "by_type": {},
            "by_asset": {},
            "total_volume": {},
            "successful_count": 0,
            "failed_count": 0
        }
        
        successful_volume = {}
        
        for transaction in transactions:
            # Estadísticas por tipo
            txn_type = transaction.transaction_type.value
            report["by_type"][txn_type] = report["by_type"].get(txn_type, 0) + 1
            
            # Estadísticas por asset
            asset = transaction.asset.value
            report["by_asset"][asset] = report["by_asset"].get(asset, 0) + 1
            
            # Volumen por asset
            if asset not in report["total_volume"]:
                report["total_volume"][asset] = 0
                successful_volume[asset] = 0
            
            report["total_volume"][asset] += abs(transaction.amount)
            successful_volume[asset] += abs(transaction.amount)
        
        report["successful_count"] = len(transactions)  # Assume all processed
        report["successful_volume"] = successful_volume
        
        return report
