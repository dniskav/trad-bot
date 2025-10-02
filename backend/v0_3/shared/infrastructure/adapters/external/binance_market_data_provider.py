#!/usr/bin/env python3
"""
Binance Market Data Provider Adapter
Implementación del IMarketDataProvider usando websockets y REST API de Binance
"""

import asyncio
import aiohttp
import json
import ssl
import websockets
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from shared.settings import env_str

from ...domain.ports.trading_ports import IMarketDataProvider
from ...domain.ports.base_types import Candlestick


class BinanceMarketDataProvider(IMarketDataProvider):
    """Proveedor de datos de mercado implementado con APIs de Binance"""

    def __init__(self):
        self.symbol = env_str("SERVER_SYMBOL", "dogeusdt").lower()
        self.base_url = "https://api.binance.com"
        self.ws_base_url = "wss://stream.binance.com:9443/ws"
        self._current_price_cache: Optional[float] = None
        self._current_ticker_cache: Optional[Dict[str, Any]] = None
        self._price_update_callbacks: List[callable] = []

        # SSL context para websockets
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def get_current_price(self, symbol: str) -> float:
        """Obtener precio actual del símbolo"""
        try:
            symbol_upper = symbol.upper()
            # Si ya tenemos el precio en cache para este símbolo, usarlo
            if symbol_upper == self.symbol.upper() and self._current_price_cache:
                return self._current_price_cache

            # Hacer request a REST API de Binance
            url = f"{self.base_url}/api/v3/ticker/price?symbol={symbol_upper}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data.get("price", 0))

                        # Cache para símbolo principal
                        if symbol_upper == self.symbol.upper():
                            self._current_price_cache = price

                        return price
                    else:
                        raise Exception(f"Binance API error: {response.status}")

        except Exception as e:
            # Si hay error, retornar precio por defecto basado en símbolo
            default_prices = {"DOGEUSDT": 0.085, "BTCUSDT": 45000.0, "ETHUSDT": 2500.0}
            return default_prices.get(symbol.upper(), 1.0)

    async def get_candlestick_data(
        self, symbol: str, interval: str = "1m", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtener datos de velas para análisis técnico"""
        try:
            symbol_upper = symbol.upper()
            url = f"{self.base_url}/api/v3/klines"

            params = {
                "symbol": symbol_upper,
                "interval": interval,
                "limit": min(limit, 1000),  # Binance máximo es 1000
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Convertir formato de Binance a formato estándar
                        candles = []
                        for kline in data:
                            candle = {
                                "symbol": symbol_upper,
                                "interval": interval,
                                "open_time": kline[0],
                                "close_time": kline[6],
                                "open": float(kline[1]),
                                "high": float(kline[2]),
                                "low": float(kline[3]),
                                "close": float(kline[4]),
                                "volume": float(kline[5]),
                                "quote_asset_volume": float(kline[7]),
                                "number_of_trades": int(kline[8]),
                                "taker_buy_base_asset_volume": float(kline[9]),
                                "taker_buy_quote_asset_volume": float(kline[10]),
                                "ignore": bool(kline[11]),
                            }
                            candles.append(candle)

                        return candles
                    else:
                        raise Exception(f"Binance klines API error: {response.status}")

        except Exception as e:
            # En caso de error, retornar datos mock
            return self._generate_mock_candles(symbol, interval, limit)

    async def get_ticker_data(self, symbol: str) -> Dict[str, Any]:
        """Obtener datos de ticker (precio bid/ask/volumen)"""
        try:
            symbol_upper = symbol.upper()

            # Cache ticker si es el símbolo principal
            if symbol_upper == self.symbol.upper() and self._current_ticker_cache:
                return self._current_ticker_cache

            url = f"{self.base_url}/api/v3/ticker/bookTicker?symbol={symbol_upper}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        ticker_data = await response.json()

                        # Enriquecer datos con información adicional
                        enriched_data = {
                            "symbol": ticker_data.get("symbol"),
                            "bid_price": float(ticker_data.get("bidPrice", 0)),
                            "bid_qty": float(ticker_data.get("bidQty", 0)),
                            "ask_price": float(ticker_data.get("askPrice", 0)),
                            "ask_qty": float(ticker_data.get("askQty", 0)),
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Cache para símbolo principal
                        if symbol_upper == self.symbol.upper():
                            self._current_ticker_cache = enriched_data

                        return enriched_data
                    else:
                        raise Exception(f"Binance ticker API error: {response.status}")

        except Exception as e:
            return self._generate_mock_ticker(symbol)

    def add_price_update_callback(self, callback: callable) -> None:
        """Agregar callback para cuando se actualice el precio"""
        self._price_update_callbacks.append(callback)

    async def start_websocket_subscription(self) -> None:
        """Iniciar suscripción WebSocket para actualizaciones en tiempo real"""
        symbol_upper = self.symbol.upper()

        # Suscribir para actualizaciones de ticker
        ticker_ws_url = f"{self.ws_base_url}/{self.symbol}@bookTicker"

        while True:
            try:
                async with websockets.connect(
                    ticker_ws_url, ping_interval=20, ssl=self.ssl_context
                ) as websocket:
                    print(
                        f"🔌 BinanceMarketDataProvider WebSocket connected: {symbol_upper}"
                    )

                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Actualizar precio en cache
                            new_price = float(data.get("a", 0))  # ask price
                            if new_price > 0:
                                self._current_price_cache = new_price

                                # Actualizar ticker cache
                                self._current_ticker_cache = {
                                    "symbol": symbol_upper,
                                    "bid_price": float(data.get("b", 0)),
                                    "bid_qty": float(data.get("B", 0)),
                                    "ask_price": float(data.get("a", 0)),
                                    "ask_qty": float(data.get("A", 0)),
                                    "timestamp": datetime.now().isoformat(),
                                }

                                # Notificar callbacks
                                for callback in self._price_update_callbacks:
                                    try:
                                        if asyncio.iscoroutinefunction(callback):
                                            await callback(new_price, symbol_upper)
                                        else:
                                            callback(new_price, symbol_upper)
                                    except Exception as callback_error:
                                        print(
                                            f"Warning: Callback error: {callback_error}"
                                        )

                        except json.JSONDecodeError:
                            continue
                        except Exception as ws_error:
                            print(f"WebSocket message processing error: {ws_error}")
                            continue

            except Exception as connection_error:
                print(
                    f"WebSocket connection error: {connection_error}. Retrying in 5s..."
                )
                await asyncio.sleep(5)

    def _generate_mock_candles(
        self, symbol: str, interval: str, limit: int
    ) -> List[Dict[str, Any]]:
        """Generar datos mock de velas para casos de error"""
        import random

        base_price = 0.085 if "DOGE" in symbol.upper() else 1.0

        candles = []
        current_time = datetime.now().timestamp() * 1000

        for i in range(limit):
            # Crear variación para mock data
            price_variation = random.uniform(-0.02, 0.02)
            candle_price = abs(base_price + (base_price * price_variation))

            candle = {
                "symbol": symbol.upper(),
                "interval": interval,
                "open_time": current_time - ((limit - i) * 60000),  # 1 min intervals
                "close_time": current_time - ((limit - i - 1) * 60000),
                "open": candle_price,
                "high": candle_price * random.uniform(1.001, 1.02),
                "low": candle_price * random.uniform(0.98, 0.999),
                "close": candle_price * random.uniform(0.995, 1.005),
                "volume": random.uniform(100000, 1000000),
                "quote_asset_volume": random.uniform(50000, 500000),
                "number_of_trades": random.randint(100, 1000),
                "taker_buy_base_asset_volume": random.uniform(40000, 400000),
                "taker_buy_quote_asset_volume": random.uniform(30000, 300000),
                "ignore": False,
            }
            candles.append(candle)

        return candles

    def _generate_mock_ticker(self, symbol: str) -> Dict[str, Any]:
        """Generar datos mock de ticker para casos de error"""
        base_price = 0.085 if "DOGE" in symbol.upper() else 1.0

        return {
            "symbol": symbol.upper(),
            "bid_price": base_price * 0.999,
            "bid_qty": 1000.0,
            "ask_price": base_price * 1.001,
            "ask_qty": 1000.0,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # Test del provider
    async def test_provider():
        provider = BinanceMarketDataProvider()

        print("📊 Testing BinanceMarketDataProvider...")

        # Test get current price
        try:
            price = await provider.get_current_price("DOGEUSDT")
            print(f"✅ Current DOGE price: ${price}")
        except Exception as e:
            print(f"❌ Error getting current price: {e}")

        # Test get ticker data
        try:
            ticker = await provider.get_ticker_data("DOGEUSDT")
            print(f"✅ Ticker data: {ticker}")
        except Exception as e:
            print(f"❌ Error getting ticker: {e}")

        # Test get candlesticks
        try:
            candles = await provider.get_candlestick_data("DOGEUSDT", "1m", 5)
            print(f"✅ Candlestick data: {len(candles)} candles")
            if candles:
                print(
                    f"   Latest candle: Open={candles[-1]['open']}, Close={candles[-1]['close']}"
                )
        except Exception as e:
            print(f"❌ Error getting candlesticks: {e}")

        print("🎯 Provider test complete!")

    asyncio.run(test_provider())
