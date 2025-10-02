#!/usr/bin/env python3
"""
Market Data Pricer Implementation
Implementación de IMarketDataPricer para obtener precios de mercado
"""

import aiohttp
from typing import Dict, Optional
from decimal import Decimal

from ...domain.models.account import AssetType
from ...domain.models.position import Money
from ...domain.ports.account_ports import IMarketDataPricer


class SimpleMarketDataPricer:
    """Preciador simple usando precios por defecto"""

    def __init__(self):
        # Precios por defecto
        self.default_prices = {
            AssetType.USDT: 1.0,  # USDT siempre es 1:1
            AssetType.DOGE: 0.085,  # ~$0.085 USD
            AssetType.BTC: 45000.0,  # ~$45,000 USD
            AssetType.ETH: 2500.0,  # ~$2,500 USD
        }

    async def get_price_usdt(self, symbol: str) -> float:
        """Obtener precio de un símbolo en USDT"""

        # Extraer asset del symbol (ej: "DOGEUSDT" -> AssetType.DOGE)
        if symbol.upper() == "USDTUSDT" or symbol.upper() == "USDT":
            return 1.0

        elif "DOGE" in symbol.upper():
            return self.default_prices[AssetType.DOGE]

        elif "BTC" in symbol.upper():
            return self.default_prices[AssetType.BTC]

        elif "ETH" in symbol.upper():
            return self.default_prices[AssetType.ETH]

        else:
            # Asset desconocido, retornar precio por defecto
            return 1.0

    async def get_multiple_prices_usdt(self, symbols: list[str]) -> Dict[str, float]:
        """Obtener múltiples precios en batch"""

        prices = {}

        for symbol in symbols:
            try:
                price = await self.get_price_usdt(symbol)
                prices[symbol.upper()] = price
            except Exception as e:
                # En caso de error, usar precio por defecto
                print(f"Warning: Failed to get price for {symbol}: {e}")
                prices[symbol.upper()] = self.default_prices.get(
                    AssetType.DOGE if "DOGE" in symbol.upper() else AssetType.USDT, 1.0
                )

        return prices

    async def calculate_conversion_rate(
        self, from_asset: AssetType, to_asset: AssetType
    ) -> Decimal:
        """Calcular tasa de conversión entre assets"""

        if from_asset == to_asset:
            return Decimal("1")

        # Convertir ambos a USDT
        from_price_usdt = self.default_prices.get(from_asset, 1.0)
        to_price_usdt = self.default_prices.get(to_asset, 1.0)

        # Calcular rate: cuántas unidades de 'to' por una de 'from'
        if from_price_usdt > 0:
            conversion_rate = Decimal(str(to_price_usdt)) / Decimal(
                str(from_price_usdt)
            )
        else:
            conversion_rate = Decimal("1")

        return conversion_rate


class BinanceMarketDataPricer(SimpleMarketDataPricer):
    """Preciador usando datos reales de Binance"""

    def __init__(self, timeout: int = 5):
        super().__init__()
        self.timeout = timeout
        self.base_url = "https://api.binance.com/api/v3"

    async def get_price_usdt(self, symbol: str) -> float:
        """Obtener precio real de Binance"""

        try:
            symbol_upper = symbol.upper()
            if not symbol_upper.endswith("USDT"):
                symbol_upper += "USDT"

            url = f"{self.base_url}/ticker/price?symbol={symbol_upper}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("price", 0))
                    else:
                        print(f"Binance API error {response.status} for {symbol}")
                        return await super().get_price_usdt(symbol)

        except Exception as e:
            print(f"Failed to fetch price for {symbol}: {e}")
            # Fallback a precios por defecto
            return await super().get_price_usdt(symbol)

    async def get_multiple_prices_usdt(self, symbols: list[str]) -> Dict[str, float]:
        """Obtener múltiples precios desde Binance"""

        # Preprocesar símbolos
        processed_symbols = []
        symbol_mapping = {}  # mapeo de símbolo procesado a original

        for symbol in symbols:
            symbol_upper = symbol.upper()
            if not symbol_upper.endswith("USDT"):
                symbol_upper += "USDT"

            processed_symbols.append(symbol_upper)
            symbol_mapping[symbol_upper] = symbol

        try:
            # Usar endpoint batch de Binance
            symbols_param = '["' + '","'.join(processed_symbols) + '"]'
            url = f"{self.base_url}/ticker/price"

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params={"symbols": symbols_param}, timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        prices_data = await response.json()

                        # Procesar respuesta
                        prices = {}
                        for price_info in prices_data:
                            symbol = price_info.get("symbol", "")
                            original_symbol = symbol_mapping.get(symbol, symbol)
                            price = float(price_info.get("price", 0))
                            prices[original_symbol.upper()] = price

                        return prices
                    else:
                        print(f"Binance batch API error: {response.status}")
                        # Fallback individual
                        return await super().get_multiple_prices_usdt(symbols)

        except Exception as e:
            print(f"Failed to fetch batch prices: {e}")
            # Fallback individual
            return await super().get_multiple_prices_usdt(symbols)


class AdvancedMarketDataPricer(BinanceMarketDataPricer):
    """Preciador avanzado con cache y funcionalidades adicionales"""

    def __init__(self, cache_duration_seconds: int = 30, timeout: int = 5):
        super().__init__(timeout)
        self.cache_duration = cache_duration_seconds
        self.price_cache: Dict[str, tuple[float, float]] = (
            {}
        )  # {symbol: (price, timestamp)}
        self.conversion_cache: Dict[tuple[AssetType, AssetType], Decimal] = {}

    async def get_price_usdt(self, symbol: str) -> float:
        """Obtener precio con cache"""

        symbol_upper = symbol.upper()

        # Verificar cache
        import time

        current_time = time.time()

        if symbol_upper in self.price_cache:
            cached_price, cache_timestamp = self.price_cache[symbol_upper]

            # Verificar si cache es válido
            if current_time - cache_timestamp < self.cache_duration:
                return cached_price

        # Cache expirado o inexistente: fetch desde Binance
        price = await super().get_price_usdt(symbol)

        # Actualizar cache
        self.price_cache[symbol_upper] = (price, current_time)

        return price

    async def calculate_conversion_rate(
        self, from_asset: AssetType, to_asset: AssetType
    ) -> Decimal:
        """Calcular conversion rate con cache"""

        cache_key = (from_asset, to_asset)

        if cache_key in self.conversion_cache:
            return self.conversion_cache[cache_key]

        # Obtener precios actuales
        from_symbol = f"{from_asset.value}USDT"
        to_symbol = f"{to_asset.value}USDT"

        try:
            prices = await self.get_multiple_prices_usdt([from_symbol, to_symbol])

            from_price = prices.get(
                from_symbol.upper(), self.default_prices.get(from_asset, 1.0)
            )
            to_price = prices.get(
                to_symbol.upper(), self.default_prices.get(to_asset, 1.0)
            )

            if from_price > 0:
                conversion_rate = Decimal(str(to_price)) / Decimal(str(from_price))
            else:
                conversion_rate = Decimal("1")

            # Cache result
            self.conversion_cache[cache_key] = conversion_rate
            reverse_cache_key = (to_asset, from_asset)
            self.conversion_cache[reverse_cache_key] = (
                Decimal("1") / conversion_rate if conversion_rate > 0 else Decimal("1")
            )

            return conversion_rate

        except Exception as e:
            print(f"Error calculating conversion rate: {e}")
            return Decimal("1")

    async def get_price_history_info(self, symbol: str) -> Dict[str, any]:
        """Obtener información histórica de precios"""

        try:
            symbol_upper = symbol.upper()
            if not symbol_upper.endswith("USDT"):
                symbol_upper += "USDT"

            url = f"{self.base_url}/ticker/24hr?symbol={symbol_upper}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        data = await response.json()

                        return {
                            "symbol": symbol_upper,
                            "price": float(data.get("lastPrice", 0)),
                            "price_change": float(data.get("priceChange", 0)),
                            "price_change_percent": float(
                                data.get("priceChangePercent", 0)
                            ),
                            "high_price": float(data.get("highPrice", 0)),
                            "low_price": float(data.get("lowPrice", 0)),
                            "volume": float(data.get("volume", 0)),
                            "count": int(data.get("count", 0)),
                        }
                    else:
                        return {"error": f"API error {response.status}"}

        except Exception as e:
            return {"error": str(e)}

    async def calculate_portfolio_value(
        self, portfolio: Dict[str, float]
    ) -> Dict[str, float]:
        """Calcular valor de portafolio en USDT"""

        symbols = list(portfolio.keys())

        # Obtener precios actuales
        prices = await self.get_multiple_prices_usdt(symbols)

        # Calcular valores
        portfolio_value = 0.0
        asset_values = {}

        for symbol, quantity in portfolio.items():
            symbol_upper = symbol.upper()
            price = prices.get(symbol_upper, 0)
            value_usdt = quantity * price

            asset_values[symbol] = {
                "quantity": quantity,
                "price_usdt": price,
                "value_usdt": value_usdt,
            }

            portfolio_value += value_usdt

        return {
            "total_value_usdt": portfolio_value,
            "assets": asset_values,
            "asset_count": len(portfolio),
        }

    def clear_cache(self):
        """Limpiar cache de precios"""
        self.price_cache.clear()
        self.conversion_cache.clear()

    def get_cache_stats(self) -> Dict[str, any]:
        """Obtener estadísticas del cache"""
        import time

        current_time = time.time()
        valid_cache_entries = 0
        expired_cache_entries = 0

        for symbol, (price, timestamp) in self.price_cache.items():
            if current_time - timestamp < self.cache_duration:
                valid_cache_entries += 1
            else:
                expired_cache_entries += 1

        return {
            "total_cache_size": len(self.price_cache),
            "valid_entries": valid_cache_entries,
            "expired_entries": expired_cache_entries,
            "cache_duration": self.cache_duration,
            "conversion_cache_size": len(self.conversion_cache),
        }
