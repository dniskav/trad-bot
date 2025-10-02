#!/usr/bin/env python3
"""
Balance Calculator Implementation
Implementación de IBalanceCalculator para cálculos de balance
"""

from typing import Dict
from decimal import Decimal

from ...domain.models.account import AccountAggregate, AssetType
from ...domain.models.position import Money
from ...domain.ports.account_ports import IBalanceCalculator


class SimpleBalanceCalculator:
    """Calculadora de balances simple pero robusta"""

    async def calculate_balances(
        self, 
        account: AccountAggregate, 
        prices: Dict[AssetType, Money]
    ) -> tuple[Money, Money]:
        """Calcular total balance y current balance en USDT"""
        
        total_value = Money.zero("USDT")
        current_value = Money.zero("USDT")
        
        # Iterar por todos los assets de la cuenta
        for asset_balance in account.assets:
            asset_type = asset_balance.asset
            
            # Obtener precio en USDT
            if asset_type == AssetType.USDT:
                # USDT siempre es 1:1
                asset_price_usdt = Money.from_float(1.0)
            else:
                asset_price_usdt = prices.get(asset_type, Money.zero("USDT"))
            
            if asset_price_usdt.amount <= 0:
                # Si no hay precio válido, usar estimación por defecto
                asset_price_usdt = self._get_default_price(asset_type)
            
            # Calcular valores
            total_amount = asset_balance.get_total_amount()  # FREE + LOCKED
            free_amount = asset_balance.free
            
            # Convertir a USDT
            total_asset_value_usdt = Money(
                total_amount.amount * asset_price_usdt.amount,
                "USDT"
            )
            current_asset_value_usdt = Money(
                free_amount.amount * asset_price_usdt.amount,
                "USDT"
            )
            
            total_value = total_value + total_asset_value_usdt
            current_value = current_value + current_asset_value_usdt
        
        return total_value, current_value

    def _get_default_price(self, asset_type: AssetType) -> Money:
        """Obtener precio por defecto para assets sin precio"""
        default_prices = {
            AssetType.USDT: Money.from_float(1.0),
            AssetType.DOGE: Money.from_float(0.085),
            AssetType.BTC: Money.from_float(45000.0),
            AssetType.ETH: Money.from_float(2500.0)
        }
        return default_prices.get(asset_type, Money.from_float(1.0))

    async def calculate_asset_value_usdt(
        self, 
        amount: Money, 
        asset_type: AssetType, 
        price_usdt: Money
    ) -> Money:
        """Calcular valor de una cantidad específica en USDT"""
        
        if asset_type == AssetType.USDT:
            return amount
        
        return Money(
            amount.amount * price_usdt.amount,
            "USDT"
        )

    async def calculate_required_margin(
        self, 
        position_value_usdt: Money, 
        leverage: int
    ) -> Money:
        """Calcular margen requerido para una posición"""
        
        if leverage <= 0:
            raise ValueError("Leverage must be positive")
        
        return Money(
            position_value_usdt.amount / Decimal(str(leverage)),
            "USDT"
        )

    async def calculate_pnl_percentage(
        self, 
        initial_balance: Money, 
        current_pnl: Money
    ) -> Decimal:
        """Calcular porcentaje de P&L"""
        
        if initial_balance.amount <= 0:
            return Decimal("0")
        
        return (current_pnl.amount / initial_balance.amount) * Decimal("100")

    async def validate_balance_sufficient(
        self, 
        account: AccountAggregate, 
        required_usdt: Money
    ) -> bool:
        """Validar si la cuenta tiene balance suficiente"""
        
        # Calcular balance disponible total en USDT
        usdt_balance = account.get_asset_balance(AssetType.USDT)
        
        if usdt_balance:
            # Convertir balance USDT libre a Money
            free_usdt = usdt_balance.free
            
            # Verificar otros assets que se puedan convertir
            other_value_usdt = Money.zero("USDT")
            
            for asset_balance in account.assets:
                if asset_balance.asset != AssetType.USDT:
                    # Usar precio estimado por defecto
                    default_price = self._get_default_price(asset_balance.asset)
                    asset_value = Money(
                        asset_balance.free.amount * default_price.amount,
                        "USDT"
                    )
                    other_value_usdt = other_value_usdt + asset_value
            
            total_available = free_usdt + other_value_usdt
            
            return total_available.amount >= required_usdt.amount
        
        return False


class AdvancedBalanceCalculator(SimpleBalanceCalculator):
    """Calculadora de balance avanzada con funcionalidades adicionales"""
    
    async def calculate_portfolio_diversification(
        self, 
        account: AccountAggregate, 
        prices: Dict[AssetType, Money]
    ) -> Dict[str, Decimal]:
        """Calcular diversificación del portafolio"""
        
        diversification = {}
        total_value, _ = await self.calculate_balances(account, prices)
        
        for asset_balance in account.assets:
            asset_type = asset_balance.asset
            
            if asset_type == AssetType.USDT:
                asset_price_usdt = Money.from_float(1.0)
            else:
                asset_price_usdt = prices.get(asset_type, self._get_default_price(asset_type))
            
            asset_total = asset_balance.get_total_amount()
            asset_value_usdt = Money(
                asset_total.amount * asset_price_usdt.amount,
                "USDT"
            )
            
            if total_value.amount > 0:
                percentage = (asset_value_usdt.amount / total_value.amount) * Decimal("100")
                diversification[asset_type.value] = percentage
        
        return diversification

    async def calculate_risk_metrics(
        self, 
        account: AccountAggregate, 
        prices: Dict[AssetType, Money]
    ) -> Dict[str, Money]:
        """Calcular métricas de riesgo"""
        
        total_value, current_value = await self.calculate_balances(account, prices)
        
        # Balance en riesgo (locked funds)
        locked_value = total_value - current_value
        
        # Porcentaje en riesgo
        risk_percentage = Decimal("0")
        if total_value.amount > 0:
            risk_percentage = (locked_value.amount / total_value.amount) * Decimal("100")
        
        return {
            "total_equity": total_value,
            "available_funds": current_value,
            "locked_funds": locked_value,
            "risk_percentage": Money(risk_percentage, "USDT")
        }

    async def calculate_performance_metrics(
        self, 
        account: AccountAggregate,
        historical_data: Dict[str, Money] = None
    ) -> Dict[str, Decimal]:
        """Calcular métricas de rendimiento"""
        
        pnl_percentage = await self.calculate_pnl_percentage(
            account.initial_balance_usdt,
            account.total_pnl
        )
        
        # Tiempo transcurrido para calcular CAGR (Compound Annual Growth Rate)
        from datetime import datetime
        
        time_elapsed = datetime.now() - account.created_at
        years_elapsed = time_elapsed.total_seconds() / (365 * 24 * 3600)
        
        if years_elapsed > 0:
            # CAGR = (Current Value / Initial Value)^(1/Years) - 1
            if account.initial_balance_usdt.amount > 0:
                cagr = (
                    (account.total_balance_usdt.amount / account.initial_balance_usdt.amount) 
                    ** (1 / years_elapsed) 
                    - 1
                ) * Decimal("100")
            else:
                cagr = Decimal("0")
        else:
            cagr = Decimal("0")
        
        return {
            "pnl_percentage": pnl_percentage,
            "cagr_percentage": cagr,
            "years_invested": Decimal(str(years_elapsed))
        }
