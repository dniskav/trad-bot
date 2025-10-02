import asyncio
import json
import aiohttp
import websockets
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from shared.logger import get_logger
from ..models.position import OpenPositionRequest, ClosePositionRequest, OrderResponse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from shared.settings import env_str

log = get_logger("server.stm_service")

STM_HTTP = "http://127.0.0.1:8100"
STM_WS = "ws://127.0.0.1:8100/ws"


class STMService:
    """Handles communication with STM (Synthetic Trading Manager)"""

    def __init__(self) -> None:
        self.stm_log_enabled = False
        self._notional_cache: Dict[str, Dict[str, Any]] = {}

    async def check_health(self) -> bool:
        """Check if STM service is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STM_HTTP}/health", timeout=5) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    return data.get("status") == "ok"
        except Exception as e:
            log.warning(f"STM health check failed: {e}")
            return False

    async def heartbeat_loop(self) -> None:
        """Maintain WebSocket connection with STM and send heartbeats"""
        while True:
            try:
                async with websockets.connect(STM_WS, ping_interval=None) as ws:
                    log.info("WS connected to STM")

                    async def pinger():
                        while True:
                            await asyncio.sleep(5)
                            await ws.send(
                                json.dumps(
                                    {
                                        "type": "ping",
                                        "ts": datetime.now(timezone.utc).isoformat(),
                                    }
                                )
                            )

                    async def receiver():
                        async for msg in ws:
                            if self.stm_log_enabled:
                                log.info(f"📨 WS msg from STM: {msg}")

                    await asyncio.gather(pinger(), receiver())
            except Exception as e:
                log.warning(f"WS error/disconnected: {e}. retrying in 3s...")
                await asyncio.sleep(3)

    async def get_socket_logging_state(self) -> dict:
        """Get current socket logging state from STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STM_HTTP}/socket/logging", timeout=5) as resp:
                    stm_state = await resp.json()
                    stm_state["server_binance_enabled"] = self.stm_log_enabled
                    return stm_state
        except aiohttp.ClientError as e:
            return {"status": "error", "message": str(e), "code": 500}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def get_min_notional(self, symbol: str) -> float:
        """Fetch and cache spot min notional for a symbol from Binance exchangeInfo."""
        try:
            sym = symbol.upper()
            cached = self._notional_cache.get(sym)
            now = datetime.now(timezone.utc).timestamp()
            if cached and (now - cached.get("ts", 0)) < 3600:
                return float(cached.get("value", 1.0))

            url = f"https://api.binance.com/api/v3/exchangeInfo?symbol={sym}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    data = await resp.json()
                    filters = (data.get("symbols", [{}])[0]).get("filters", [])
                    min_notional = 1.0
                    for f in filters:
                        if f.get("filterType") in ("NOTIONAL", "MIN_NOTIONAL"):
                            min_notional = float(
                                f.get("minNotional") or f.get("notional") or 1.0
                            )
                            break
                    self._notional_cache[sym] = {"value": min_notional, "ts": now}
                    return float(min_notional)
        except Exception:
            return 1.0

    async def set_socket_logging_state(self, payload: dict) -> dict:
        """Set socket logging state in STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STM_HTTP}/socket/logging", json=payload, timeout=5
                ) as resp:
                    return await resp.json()
        except aiohttp.ClientError as e:
            return {"status": "error", "message": str(e), "code": 500}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def open_position(self, request: OpenPositionRequest) -> OrderResponse:
        """Open a position via STM using Binance-compatible format"""
        try:
            # Convert to Binance format
            binance_data = {
                "symbol": request.symbol,
                "side": request.side,
                "type": request.type,
                "quantity": request.quantity,
                "timeInForce": request.timeInForce or "GTC",
                "newOrderRespType": "RESULT",
                "sideEffectType": "NO_SIDE_EFFECT",
                "isIsolated": "TRUE" if request.isIsolated else "FALSE",
                "newClientOrderId": request.clientOrderId,
            }

            # Add leverage if provided
            if request.leverage:
                binance_data["leverage"] = request.leverage

            # Add price if LIMIT order
            if request.type == "LIMIT" and request.price:
                binance_data["price"] = request.price

            # Add stopPrice if STOP order
            if request.type in ["STOP_MARKET", "STOP_LOSS"] and request.stopPrice:
                binance_data["stopPrice"] = request.stopPrice

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STM_HTTP}/sapi/v1/margin/order", json=binance_data, timeout=20
                ) as resp:
                    response_data = await resp.json()
                    return OrderResponse(**response_data)
        except aiohttp.ClientError as e:
            return OrderResponse(
                success=False,
                orderId="",
                message=f"STM error: {str(e)}",
            )
        except Exception as e:
            return OrderResponse(
                success=False, orderId="", message=f"Error connecting to STM: {str(e)}"
            )

    async def close_position(self, request: ClosePositionRequest) -> OrderResponse:
        """Close a position via STM"""
        try:
            data = request.dict()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STM_HTTP}/sapi/v1/margin/close", json=data, timeout=10
                ) as resp:
                    response_data = await resp.json()
                    return OrderResponse(**response_data)
        except aiohttp.ClientError as e:
            return OrderResponse(
                success=False,
                orderId="",
                message=f"STM error: {str(e)}",
            )
        except Exception as e:
            return OrderResponse(
                success=False, orderId="", message=f"Error connecting to STM: {str(e)}"
            )

    async def get_positions(self, status: Optional[str] = None) -> Dict[str, Any]:
        """Get positions from STM"""
        try:
            url = f"{STM_HTTP}/sapi/v1/margin/positions"
            if status:
                url += f"?status={status}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    positions = await resp.json()
                    return {
                        "success": True,
                        "positions": positions,
                        "count": len(positions),
                    }
        except Exception as e:
            return {"success": False, "message": f"Error connecting to STM: {str(e)}"}

    async def get_position(self, position_id: str) -> Dict[str, Any]:
        """Get a specific position from STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{STM_HTTP}/positions/{position_id}", timeout=5
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"success": False, "message": f"Error connecting to STM: {str(e)}"}

    async def get_position_orders(self, position_id: str) -> Dict[str, Any]:
        """Get orders for a position from STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{STM_HTTP}/positions/{position_id}/orders", timeout=5
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"success": False, "message": f"Error connecting to STM: {str(e)}"}

    async def get_all_orders(self) -> Dict[str, Any]:
        """Get all orders from STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{STM_HTTP}/positions/orders/all", timeout=5
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {
                "success": False,
                "message": f"Error connecting to STM: {str(e)}",
            }

    async def reset_positions_orders(self) -> Dict[str, Any]:
        """Reset positions and orders in STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STM_HTTP}/positions/admin/reset", json={}, timeout=5
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"success": False, "message": f"Error connecting to STM: {str(e)}"}

    async def set_stop_loss(self, position_id: str, price: str) -> Dict[str, Any]:
        """Create/Update SL for a position in STM using Binance format"""
        try:
            # Get position details first to determine side
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STM_HTTP}/sapi/v1/margin/positions") as resp:
                    positions = await resp.json()
                    position = next(
                        (p for p in positions if p.get("positionId") == position_id),
                        None,
                    )
                    if not position:
                        return {"success": False, "message": "Position not found"}

                    # Determine opposite side for SL
                    position_side = (
                        "BUY" if float(position["positionAmt"]) > 0 else "SELL"
                    )
                    sl_side = "SELL" if position_side == "BUY" else "BUY"

                    # Create SL order in Binance format
                    sl_data = {
                        "symbol": position["symbol"],
                        "side": sl_side,
                        "type": "STOP_MARKET",
                        "quantity": position["positionAmt"],
                        "stopPrice": price,
                        "timeInForce": "GTC",
                        "newOrderRespType": "RESULT",
                        "sideEffectType": "NO_SIDE_EFFECT",
                        "isIsolated": "TRUE" if position.get("isolated") else "FALSE",
                        "newClientOrderId": f"sl-{position_id}",
                    }

                    async with session.post(
                        f"{STM_HTTP}/sapi/v1/margin/order", json=sl_data, timeout=5
                    ) as sl_resp:
                        sl_result = await sl_resp.json()

                        # If SL order was created successfully, update position with the order ID
                        if sl_result.get("success") and sl_result.get("orderId"):
                            # The STM automatically updates the position with stopLossOrderId
                            # when it processes the SL order, so we just return the result
                            pass

                        return sl_result
        except Exception as e:
            return {"success": False, "message": f"Error setting SL: {str(e)}"}

    async def set_take_profit(self, position_id: str, price: str) -> Dict[str, Any]:
        """Create/Update TP for a position in STM using Binance format"""
        try:
            # Get position details first to determine side
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STM_HTTP}/sapi/v1/margin/positions") as resp:
                    positions = await resp.json()
                    position = next(
                        (p for p in positions if p.get("positionId") == position_id),
                        None,
                    )
                    if not position:
                        return {"success": False, "message": "Position not found"}

                    # Determine opposite side for TP
                    position_side = (
                        "BUY" if float(position["positionAmt"]) > 0 else "SELL"
                    )
                    tp_side = "SELL" if position_side == "BUY" else "BUY"

                    # Create TP order in Binance format
                    tp_data = {
                        "symbol": position["symbol"],
                        "side": tp_side,
                        "type": "LIMIT",
                        "quantity": position["positionAmt"],
                        "price": price,
                        "timeInForce": "GTC",
                        "newOrderRespType": "RESULT",
                        "sideEffectType": "NO_SIDE_EFFECT",
                        "isIsolated": "TRUE" if position.get("isolated") else "FALSE",
                        "newClientOrderId": f"tp-{position_id}",
                    }

                    async with session.post(
                        f"{STM_HTTP}/sapi/v1/margin/order", json=tp_data, timeout=5
                    ) as tp_resp:
                        tp_result = await tp_resp.json()

                        # If TP order was created successfully, update position with the order ID
                        if tp_result.get("success") and tp_result.get("orderId"):
                            # The STM automatically updates the position with takeProfitOrderId
                            # when it processes the TP order, so we just return the result
                            pass

                        return tp_result
        except Exception as e:
            return {"success": False, "message": f"Error setting TP: {str(e)}"}

    async def get_account_synth(self) -> dict:
        """Get synthetic account data from STM with additional available balance fields"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{STM_HTTP}/account/synth", timeout=5) as resp:
                    account_data = await resp.json()

                    # Agregar campos de balance disponible
                    if account_data and not account_data.get("status") == "error":
                        usdt_balance = float(account_data.get("usdt_balance", 0))
                        doge_balance = float(account_data.get("doge_balance", 0))
                        usdt_locked = float(account_data.get("usdt_locked", 0))
                        doge_locked = float(account_data.get("doge_locked", 0))
                        doge_price = float(account_data.get("doge_price", 0))

                        # Calcular balances disponibles (excluyendo fondos bloqueados)
                        # Clamp locked to non-negative to avoid distorted balances
                        usdt_locked = max(0.0, usdt_locked)
                        doge_locked = max(0.0, doge_locked)
                        available_usdt = max(0.0, usdt_balance - usdt_locked)
                        available_doge = max(0.0, doge_balance - doge_locked)
                        available_balance_usdt = available_usdt + (
                            available_doge * doge_price
                        )

                        # Agregar campos al response
                        account_data["available_usdt"] = available_usdt
                        account_data["available_doge"] = available_doge
                        account_data["available_balance_usdt"] = available_balance_usdt
                        account_data["trading_power_usdt"] = available_balance_usdt
                        account_data["max_position_size_usdt"] = available_balance_usdt

                    return account_data
        except aiohttp.ClientError as e:
            return {"status": "error", "message": str(e), "code": 500}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def reset_account_synth(self) -> dict:
        """Reset synthetic account via STM"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{STM_HTTP}/account/synth/reset", json={}, timeout=5
                ) as resp:
                    return await resp.json()
        except aiohttp.ClientError as e:
            return {"status": "error", "message": str(e), "code": 500}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}
