#!/usr/bin/env python3
"""
STM Trading Executor Adapter
Implementación del ITradingExecutor usando servicios STM existentes
"""

import asyncio
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime
from backend.shared.logger import get_logger

from ...domain.ports.trading_ports import ITradingExecutor
from ...domain.ports.base_types import OrderResult

log = get_logger("stm_trading_executor")


class STMTradingExecutor(ITradingExecutor):
    """Ejecutor de trading que usa servicios STM internos"""

    def __init__(self, stm_base_url: str = "http://127.0.0.1:8100"):
        self.stm_base_url = stm_base_url
        self.timeout = 20  # Timeout para requests

    async def execute_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> OrderResult:
        """Ejecutar orden market usando STM"""
        try:
            log.info(f"Executing market order: {side} {quantity} {symbol}")

            # Construir payload compatible con STM
            order_data = {
                "symbol": symbol,
                "side": side,
                "type": "MARKET",
                "quantity": str(int(quantity)),  # STM espera integer
                "timeInForce": "GTC",
                "newOrderRespType": "RESULT",
                "sideEffectType": "NO_SIDE_EFFECT",
                "isIsolated": "FALSE",
            }

            # Obtener precio de ejecución de Binance para simular orden market
            execution_price = await self._get_execution_price(symbol)
            order_data["price"] = str(execution_price)

            # Ejecutar orden via STM
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.stm_base_url}/sapi/v1/margin/order",
                    json=order_data,
                    timeout=self.timeout,
                ) as response:

                    response_data = await response.json()

                    if response.status == 200 and response_data.get("success", False):
                        log.info(
                            f"✅ Market order executed: {response_data.get('orderId')}"
                        )

                        return OrderResult(
                            success=True,
                            order_id=response_data.get("orderId", ""),
                            message="Market order executed successfully",
                            executed_price=execution_price,
                            executed_quantity=quantity,
                            timestamp=datetime.now().isoformat(),
                        )
                    else:
                        error_msg = response_data.get("message", "Unknown STM error")
                        log.error(f"❌ Market order failed: {error_msg}")

                        return OrderResult(
                            success=False,
                            order_id="",
                            message=f"STM execution failed: {error_msg}",
                            timestamp=datetime.now().isoformat(),
                        )

        except asyncio.TimeoutError:
            log.error("⏰ STM execution timeout")
            return OrderResult(
                success=False,
                order_id="",
                message="STM execution timeout",
                timestamp=datetime.now().isoformat(),
            )
        except Exception as e:
            log.error(f"💥 STM execution error: {e}")
            return OrderResult(
                success=False,
                order_id="",
                message=f"STM execution error: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )

    async def execute_limit_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> OrderResult:
        """Ejecutar orden limit usando STM"""
        try:
            log.info(f"Executing limit order: {side} {quantity} {symbol} @ {price}")

            order_data = {
                "symbol": symbol,
                "side": side,
                "type": "LIMIT",
                "quantity": str(int(quantity)),
                "price": str(price),
                "timeInForce": "GTC",
                "newOrderRespType": "RESULT",
                "sideEffectType": "NO_SIDE_EFFECT",
                "isIsolated": "FALSE",
            }

            # Para LIMIT orders, STM las coloca inmediatamente (simulado)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.stm_base_url}/sapi/v1/margin/order",
                    json=order_data,
                    timeout=self.timeout,
                ) as response:

                    response_data = await response.json()

                    if response.status == 200 and response_data.get("success", False):
                        log.info(
                            f"✅ Limit order placed: {response_data.get('orderId')}"
                        )

                        return OrderResult(
                            success=True,
                            order_id=response_data.get("orderId", ""),
                            message="Limit order placed successfully",
                            executed_price=price,
                            executed_quantity=quantity,
                            timestamp=datetime.now().isoformat(),
                        )
                    else:
                        error_msg = response_data.get("message", "Unknown STM error")
                        log.error(f"❌ Limit order failed: {error_msg}")

                        return OrderResult(
                            success=False,
                            order_id="",
                            message=f"STM placement failed: {error_msg}",
                            timestamp=datetime.now().isoformat(),
                        )

        except Exception as e:
            log.error(f"💥 STM limit order error: {e}")
            return OrderResult(
                success=False,
                order_id="",
                message=f"STM limit error: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )

    async def execute_stop_order(
        self, symbol: str, side: str, quantity: float, stop_price: float
    ) -> OrderResult:
        """Ejecutar orden stop usando STM"""
        try:
            log.info(
                f"Executing stop order: {side} {quantity} {symbol} stop@{stop_price}"
            )

            order_data = {
                "symbol": symbol,
                "side": side,
                "type": "STOP_MARKET",
                "quantity": str(int(quantity)),
                "stopPrice": str(stop_price),
                "timeInForce": "GTC",
                "newOrderRespType": "RESULT",
                "sideEffectType": "NO_SIDE_EFFECT",
                "isIsolated": "FALSE",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.stm_base_url}/sapi/v1/margin/order",
                    json=order_data,
                    timeout=self.timeout,
                ) as response:

                    response_data = await response.json()

                    if response.status == 200 and response_data.get("success", False):
                        log.info(
                            f"✅ Stop order placed: {response_data.get('orderId')}"
                        )

                        return OrderResult(
                            success=True,
                            order_id=response_data.get("orderId", ""),
                            message="Stop order placed successfully",
                            executed_price=0.0,  # Stop orders are not executed yet
                            executed_quantity=0.0,
                            timestamp=datetime.now().isoformat(),
                        )
                    else:
                        error_msg = response_data.get("message", "Unknown STM error")
                        log.error(f"❌ Stop order failed: {error_msg}")

                        return OrderResult(
                            success=False,
                            order_id="",
                            message=f"STM stop order failed: {error_msg}",
                            timestamp=datetime.now().isoformat(),
                        )

        except Exception as e:
            log.error(f"💥 STM stop order error: {e}")
            return OrderResult(
                success=False,
                order_id="",
                message=f"STM stop error: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancelar orden usando STM"""
        try:
            log.info(f"Cancelling order: {order_id}")

            # STM podría tener una endpoint para cancelar órdenes
            # Por ahora simulamos cancelación exitosa
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"{self.stm_base_url}/sapi/v1/margin/order/{order_id}",
                    timeout=self.timeout,
                ) as response:

                    if response.status in [200, 204]:
                        log.info(f"✅ Order cancelled: {order_id}")
                        return True
                    else:
                        response_data = await response.json()
                        error_msg = response_data.get("message", "Cancel failed")
                        log.error(f"❌ Cancel order failed: {error_msg}")
                        return False

        except Exception as e:
            log.error(f"💥 STM cancel error: {e}")
            return False

    async def _get_execution_price(self, symbol: str) -> float:
        """Obtener precio de ejecución desde Binance"""
        try:
            import aiohttp

            symbol_upper = symbol.upper()
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_upper}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return float(data.get("price", 0))
                    else:
                        # Precio por defecto si falla la API
                        default_prices = {
                            "DOGEUSDT": 0.085,
                            "BTCUSDT": 45000.0,
                            "ETHUSDT": 2500.0,
                        }
                        return default_prices.get(symbol_upper, 1.0)

        except Exception as e:
            log.warning(f"Could not fetch execution price for {symbol}: {e}")
            return 0.085  # Default DOGE price

    async def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Obtener estado de una orden"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.stm_base_url}/sapi/v1/margin/order/{order_id}", timeout=10
                ) as response:

                    if response.status == 200:
                        return await response.json()
                    else:
                        return None

        except Exception as e:
            log.error(f"Error getting order status {order_id}: {e}")
            return None

    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtener órdenes abiertas"""
        try:
            url = f"{self.stm_base_url}/sapi/v1/margin/openOrders"
            params = {}

            if symbol:
                params["symbol"] = symbol.upper()

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:

                    if response.status == 200:
                        return await response.json()
                    else:
                        return []

        except Exception as e:
            log.error(f"Error getting open orders: {e}")
            return []


if __name__ == "__main__":
    # Test del executor
    async def test_executor():
        executor = STMTradingExecutor()

        print("⚡ Testing STMTradingExecutor...")

        # Test market order (esto requerirá que STM esté corriendo)
        try:
            result = await executor.execute_market_order("DOGEUSDT", "BUY", 100.0)
            print(f"✅ Market order result: {result.success} - {result.message}")
        except Exception as e:
            print(f"❌ Market order test error: {e}")

        # Test limit order
        try:
            result = await executor.execute_limit_order("DOGEUSDT", "SELL", 50.0, 0.090)
            print(f"✅ Limit order result: {result.success} - {result.message}")
        except Exception as e:
            print(f"❌ Limit order test error: {e}")

        print("🎯 Executor test complete!")

    # Comentado para evitar ejecutar automáticamente sin STM corriendo
    # asyncio.run(test_executor())
