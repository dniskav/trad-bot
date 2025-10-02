#!/usr/bin/env python3
"""
Commission Calculator Implementation
Implementación de IAccountCommissionCalculator para cálculo de comisiones
"""

from decimal import Decimal
from typing import Dict, Optional

from ...domain.models.position import Money
from ...domain.models.account import AssetType
from ...domain.ports.account_ports import IAccountCommissionCalculator


class StandardCommissionCalculator:
    """Calculadora de comisiones estándar"""

    def __init__(self):
        # Tasas de comisión por defecto (0.1% para Binance)
        self.default_commission_rates = {
            AssetType.USDT: Decimal("0.001"),  # 0.1%
            AssetType.DOGE: Decimal("0.001"),
            AssetType.BTC: Decimal("0.001"),
            AssetType.ETH: Decimal("0.001")
        }
        
        # Comisiones mínimas por asset (para evitar comisiones muy pequeñas)
        self.minimum_commission = {
            AssetType.USDT: Money.from_float(0.01),  # Mínimo $0.01
            AssetType.DOGE: Money.from_float(1.0),     # Mínimo 1 DOGE
            AssetType.BTC: Money.from_float(0.000001), # Mínimo 0.000001 BTC
            AssetType.ETH: Money.from_float(0.0001)   # Mínimo 0.0001 ETH
        }

    async def calculate_commission(
        self, 
        trade_value: Money, 
        asset: AssetType,
        commission_rate: Optional[Decimal] = None
    ) -> Money:
        """Calcular comisión para una operación"""
        
        # Usar tasa por defecto si no se especifica una
        if commission_rate is None:
            commission_rate = self.default_commission_rates.get(
                asset, 
                Decimal("0.001")
            )
        
        # Verificar que el rate sea válido
        if commission_rate < 0 or commission_rate > Decimal("1.0"):
            raise ValueError(f"Invalid commission rate: {commission_rate}")
        
        # Calcular comisión
        commission_amount = Money(
            trade_value.amount * commission_rate,
            asset.value
        )
        
        # Aplicar comisión mínima
        min_commission = self.minimum_commission.get(asset, Money.zero(asset.value))
        if commission_amount.amount < min_commission.amount:
            commission_amount = min_commission
        
        return commission_amount

    async def calculate_maker_commission(
        self, 
        trade_value: Money, 
        asset: AssetType
    ) -> Money:
        """Calcular comisión de maker (limit order que agrega liquidez)"""
        
        # Maker commissions suelen ser más bajas
        maker_rate = Decimal("0.0008")  # 0.08%
        
        return await self.calculate_commission(trade_value, asset, maker_rate)

    async def calculate_taker_commission(
        self, 
        trade_value: Money, 
        asset: AssetType
    ) -> Money:
        """Calcular comisión de taker (market order que toma liquidez)"""
        
        # Taker commissions son estándares
        taker_rate = Decimal("0.001")  # 0.1%
        
        return await self.calculate_commission(trade_value, asset, taker_rate)

    async def calculate_funding_fee(
        self, 
        position_value: Money, 
        funding_rate: Decimal,
        hours_held: Decimal = Decimal("8")  # Binance cobra cada 8 horas
    ) -> Money:
        """Calcular comisión de funding para posiciones con margen"""
        
        if funding_rate < 0 or funding_rate > Decimal("1.0"):
            raise ValueError(f"Invalid funding rate: {funding_rate}")
        
        # Funding fee = Position Value * Funding Rate
        funding_amount = Money(
            position_value.amount * funding_rate,
            position_value.currency
        )
        
        return funding_amount

    async def calculate_vip_commission(
        self, 
        trade_value: Money, 
        asset: AssetType,
        vip_level: int
    ) -> Money:
        """Calcular comisión VIP según nivel de trading"""
        
        # Tasas VIP de Binance (aproximadas)
        vip_rates = {
            0: Decimal("0.001"),   # VIP 0: ~0.1%
            1: Decimal("0.0009"),  # VIP 1: ~0.09%
            2: Decimal("0.0008"),  # VIP 2: ~0.08%
            3: Decimal("0.0007"),  # VIP 3: ~0.07%
            4: Decimal("0.0006"),  # VIP 4: ~0.06%
            5: Decimal("0.0005"),  # VIP 5: ~0.05%
            6: Decimal("0.0004"),  # VIP 6: ~0.04%
            7: Decimal("0.0003"),  # VIP 7: ~0.03%
            8: Decimal("0.0002"),  # VIP 8: ~0.02%
            9: Decimal("0.0001"),  # VIP 9: ~0.01%
        }
        
        # Limitar VIP level
        vip_level = max(0, min(vip_level, 9))
        rate = vip_rates[vip_level]
        
        return await self.calculate_commission(trade_value, asset, rate)

    async def calculate_volume_discount(
        self, 
        monthly_volume: Money,
        commission_rate: Decimal
    ) -> Decimal:
        """Calcular descuento por volumen mensual"""
        
        # Descuentos basados en volumen mensual (en USDT)
        volume_usdt = monthly_volume.amount
        
        discount_tiers = [
            (Decimal("50000"), Decimal("0.05")),   # 5% descuento >$50k
            (Decimal("100000"), Decimal("0.10")),  # 10% descuento >$100k
            (Decimal("500000"), Decimal("0.15")),  # 15% descuento >$500k
            (Decimal("1000000"), Decimal("0.20")), # 20% descuento >$1M
            (Decimal("5000000"), Decimal("0.25")), # 25% descuento >$5M
        ]
        
        # Encontrar tier aplicado
        applied_discount = Decimal("0")
        for volume_threshold, discount_rate in discount_tiers:
            if volume_usdt >= volume_threshold:
                applied_discount = discount_rate
        
        # Aplicar descuento
        effective_rate = commission_rate * (Decimal("1") - applied_discount)
        
        return effective_rate

    def get_commission_estimate(
        self, 
        trade_value_usdt: Decimal,
        trade_count: int = 1
    ) -> Dict[str, Decimal]:
        """Obtener estimación de comisiones para múltiples trades"""
        
        # Tasa estándar
        standard_rate = Decimal("0.001")
        
        # Calcular por diferentes activos
        estimates = {}
        
        for asset in [AssetType.USDT, AssetType.DOGE, AssetType.BTC, AssetType.ETH]:
            # Convertir valor de trade a currency del asset
            if asset == AssetType.USDT:
                asset_value = Money(trade_value_usdt, "USDT")
                commission = Money(trade_value_usdt * standard_rate, "USDT")
            elif asset == AssetType.DOGE:
                # Asumir precio DOGE = $0.085
                doge_price = Decimal("0.085")
                asset_amount = trade_value_usdt / doge_price
                asset_value = Money(asset_amount, "DOGE")
                commission = Money(asset_amount * standard_rate, "DOGE")
            elif asset == AssetType.BTC:
                # Asumir precio BTC = $45,000
                btc_price = Decimal("45000")
                asset_amount = trade_value_usdt / btc_price
                asset_value = Money(asset_amount, "BTC")
                commission = Money(asset_amount * standard_rate, "BTC")
            elif asset == AssetType.ETH:
                # Asumir precio ETH = $2,500
                eth_price = Decimal("2500")
                asset_amount = trade_value_usdt / eth_price
                asset_value = Money(asset_amount, "ETH")
                commission = Money(asset_amount * standard_rate, "ETH")
            
            estimates[asset.value] = {
                "asset_value": str(asset_value.amount),
                "commission_amount": str(commission.amount),
                "commission_percent": float(standard_rate * Decimal("100"))
            }
        
        return estimates


class AdvancedCommissionCalculator(StandardCommissionCalculator):
    """Calculadora de comisiones avanzada con características adicionales"""
    
    def __init__(self):
        super().__init__()
        
        # Tasas diferenciadas por tipo de orden
        self.order_type_rates = {
            "MARKET": Decimal("0.001"),    # Market orders
            "LIMIT": Decimal("0.0008"),    # Limit orders
            "STOP_MARKET": Decimal("0.001"), # Stop market
            "STOP_LIMIT": Decimal("0.0008"), # Stop limit
        }

    async def calculate_order_type_commission(
        self, 
        trade_value: Money, 
        asset: AssetType,
        order_type: str
    ) -> Money:
        """Calcular comisión basada en tipo de orden"""
        
        rate = self.order_type_rates.get(order_type, Decimal("0.001"))
        return await self.calculate_commission(trade_value, asset, rate)

    async def calculate_dynamic_commission(
        self, 
        trade_value: Money, 
        asset: AssetType,
        market_conditions: Dict[str, float] = None
    ) -> Money:
        """Calcular comisión dinámica basada en condiciones de mercado"""
        
        base_rate = self.default_commission_rates.get(asset, Decimal("0.001"))
        
        # Ajustar según condiciones de mercado
        if market_conditions:
            volatility = market_conditions.get("volatility", 0.0)
            volume = market_conditions.get("volume_24h", 1000000.0)
            
            # Alta volatilidad = comisión ligeramente mayor
            if volatility > 0.05:  # >5%
                base_rate *= Decimal("1.05")
            
            # Alto volumen = comisión ligeramente menor
            if volume > 5000000:  # >$5M 24h volume
                base_rate *= Decimal("0.95")
        
        return await self.calculate_commission(trade_value, asset, base_rate)

    async def calculate_fees_summary(
        self, 
        trades: list[Dict[str, any]]
    ) -> Dict[str, Decimal]:
        """Calcular resumen de comisiones para múltiples trades"""
        
        total_trades = len(trades)
        total_commission_usdt = Decimal("0")
        total_value_usdt = Decimal("0")
        
        for trade in trades:
            trade_value = Money.from_float(trade.get("value_usdt", 0))
            asset = AssetType(trade.get("asset", "USDT"))
            order_type = trade.get("order_type", "MARKET")
            
            # Calcular comisión
            commission = await self.calculate_order_type_commission(
                trade_value, asset, order_type
            )
            
            # Convertir a USDT para sumar
            if commission.currency == "USDT":
                commission_usdt = commission.amount
            elif commission.currency == "DOGE":
                commission_usdt = commission.amount * Decimal("0.085")
            elif commission.currency == "BTC":
                commission_usdt = commission.amount * Decimal("45000")
            elif commission.currency == "ETH":
                commission_usdt = commission.amount * Decimal("2500")
            else:
                commission_usdt = commission.amount
            
            total_commission_usdt += commission_usdt
            total_value_usdt += trade_value.amount
        
        # Calcular eficiencia
        average_rate = Decimal("0")
        if total_value_usdt > 0:
            average_rate = (total_commission_usdt / total_value_usdt) * Decimal("100")
        
        return {
            "total_trades": Decimal(str(total_trades)),
            "total_value_usdt": total_value_usdt,
            "total_commission_usdt": total_commission_usdt,
            "average_commission_rate": average_rate,
            "average_commission_per_trade": total_commission_usdt / Decimal(str(total_trades)) if total_trades > 0 else Decimal("0")
        }
