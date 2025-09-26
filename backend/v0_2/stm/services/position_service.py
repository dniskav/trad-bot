import os
import json
import uuid
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone
from backend.shared.persistence import JsonStore
from backend.shared.logger import get_logger
from ..models.position import (
    Position,
    BinanceMarginOrderRequest,
    OpenPositionRequest,
    ClosePositionRequest,
    OrderResponse,
)

log = get_logger("stm.position_service")

# Persistencia para posiciones
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
STORE = JsonStore(DATA_DIR)
POSITIONS_FILE = "positions"
ORDERS_FILE = "orders"

# Precio actual (se actualiza desde Binance service)
_current_price: Optional[float] = None


class PositionService:
    def __init__(
        self, on_position_change: Optional[Callable] = None, account_service=None
    ):
        self.store = STORE
        self.positions_file = POSITIONS_FILE
        self.orders_file = ORDERS_FILE
        self.on_position_change = on_position_change
        self.account_service = account_service

    def _generate_id(self) -> str:
        """Generate unique ID"""
        return str(uuid.uuid4())

    async def _notify_position_change(
        self, change_type: str, position_data: Dict[str, Any]
    ):
        """Notify about position changes"""
        if self.on_position_change:
            try:
                await self.on_position_change(change_type, position_data)
            except Exception as e:
                log.error(f"Error notifying position change: {e}")

    def _calculate_commission(self, quantity: float, price: float, side: str) -> float:
        """Calculate commission based on Binance fees (0.1% for spot, 0.02% for futures)"""
        # Using spot trading fees (0.1% = 0.001)
        commission_rate = 0.001
        notional = quantity * price
        return notional * commission_rate

    @staticmethod
    def _parse_optional_price(value: Any) -> Optional[str]:
        """Attempt to parse an incoming SL/TP price to float; return stringified float or None.
        If value is not numeric, returns None to ignore it.
        """
        try:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return str(float(value))
            if isinstance(value, str):
                v = value.strip()
                if v == "" or v.lower() in ("none", "null", "nan"):
                    return None
                return str(float(v))
        except Exception:
            return None
        return None

    async def _update_account_balance(
        self, position_data: Dict[str, Any], change_type: str
    ):
        """Update account balance when position changes"""
        if not self.account_service:
            return

        try:
            account = await self.account_service.get_account()
            quantity = float(position_data.get("quantity", 0))
            entry_price = float(position_data.get("entryPrice", 0))
            side = position_data.get("side", "BUY")

            # Calculate commission
            commission = self._calculate_commission(quantity, entry_price, side)

            if change_type == "opened":
                # When opening position: lock funds and pay commission
                notional = quantity * entry_price

                if side == "BUY":
                    # BUY: lock USDT for purchase + commission
                    account["usdt_locked"] += notional + commission
                    account["usdt_balance"] -= commission  # Pay commission immediately
                else:
                    # SELL: lock DOGE for sale + commission
                    account["doge_locked"] += quantity + (commission / entry_price)
                    account["doge_balance"] -= (
                        commission / entry_price
                    )  # Pay commission in DOGE

            elif change_type == "closed":
                # When closing position: unlock funds and pay commission
                notional = quantity * entry_price
                current_price = self._get_current_price(
                    position_data.get("symbol", "DOGEUSDT")
                )
                exit_notional = quantity * current_price

                if side == "BUY":
                    # BUY position closing: unlock USDT, receive DOGE, pay commission
                    account["usdt_locked"] -= notional
                    account["doge_balance"] += quantity - (commission / current_price)
                    account["usdt_balance"] -= commission  # Pay exit commission
                else:
                    # SELL position closing: unlock DOGE, receive USDT, pay commission
                    account["doge_locked"] -= quantity + (commission / entry_price)
                    account["usdt_balance"] += exit_notional - commission

            # Recompute balances
            account = self.account_service._compute_balances(account)
            account["last_updated"] = datetime.now(timezone.utc).isoformat()

            # Save updated account
            self.account_service.store.write(self.account_service.account_file, account)

            log.info(
                f"Account balance updated for {change_type} position: commission={commission:.6f}"
            )

        except Exception as e:
            log.error(f"Error updating account balance: {e}")

    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        # For now, return a default price for DOGEUSDT
        # In production, this would fetch from Binance
        if symbol.upper() == "DOGEUSDT":
            return _current_price or 0.085  # Default DOGE price
        return 1.0  # Default for other symbols

    def _calculate_position_value(self, quantity: float, price: float) -> float:
        """Calculate position value"""
        return quantity * price

    def _calculate_pnl(self, position: Position, current_price: float) -> float:
        """Calculate current P&L for position"""
        entry_price = float(position.entryPrice)
        quantity = float(position.quantity)

        if position.side == "BUY":
            pnl = (current_price - entry_price) * quantity
        else:  # SELL
            pnl = (entry_price - current_price) * quantity

        return pnl

    def _update_position_pnl(self, position: Position) -> Position:
        """Update position P&L based on current price"""
        current_price = self._get_current_price(position.symbol)
        position.pnl = self._calculate_pnl(position, current_price)
        position.updatedAt = datetime.now(timezone.utc).isoformat()
        return position

    def _load_positions(self) -> List[Dict[str, Any]]:
        """Load positions from storage"""
        return self.store.read(self.positions_file, [])

    def _save_positions(self, positions: List[Dict[str, Any]]) -> None:
        """Save positions to storage"""
        self.store.write(self.positions_file, positions)

    def _load_orders(self) -> List[Dict[str, Any]]:
        """Load orders from storage"""
        return self.store.read(self.orders_file, [])

    def _save_orders(self, orders: List[Dict[str, Any]]) -> None:
        """Save orders to storage"""
        self.store.write(self.orders_file, orders)

    async def reset_positions_and_orders(self) -> Dict[str, int]:
        """Clear all synthetic positions and orders (testing utility)."""
        try:
            current_positions = self._load_positions() or []
            current_orders = self._load_orders() or []

            self._save_positions([])
            self._save_orders([])

            log.info(
                f"Reset positions and orders (cleared {len(current_positions)} positions, {len(current_orders)} orders)"
            )

            return {
                "positions_cleared": len(current_positions),
                "orders_cleared": len(current_orders),
            }
        except Exception as e:
            log.error(f"Error resetting positions/orders: {e}")
            return {"positions_cleared": 0, "orders_cleared": 0}

    async def binance_margin_order(
        self, request: BinanceMarginOrderRequest
    ) -> OrderResponse:
        """Handle Binance margin order - exact format from Binance API"""
        try:
            # Generate order ID
            order_id = self._generate_id()

            # Get current price for MARKET orders
            current_price = self._get_current_price(request.symbol)

            # Validate order type specific requirements
            if request.type == "LIMIT" and not request.price:
                return OrderResponse(
                    success=False,
                    orderId=order_id,
                    message="LIMIT order requires price parameter",
                )

            if request.type in ["STOP_MARKET", "STOP_LOSS"] and not request.stopPrice:
                return OrderResponse(
                    success=False,
                    orderId=order_id,
                    message="STOP order requires stopPrice parameter",
                )

            # Determine execution price
            if request.type == "MARKET":
                execution_price = str(current_price)
            elif request.type == "LIMIT":
                execution_price = request.price
            else:
                execution_price = str(
                    current_price
                )  # For stop orders, use current price

            # Create order record
            order_data = {
                "orderId": order_id,
                "clientOrderId": request.newClientOrderId or order_id,
                "symbol": request.symbol,
                "side": request.side,
                "type": request.type,
                "quantity": request.quantity,
                "price": execution_price,
                "stopPrice": request.stopPrice,
                "timeInForce": request.timeInForce,
                "status": "FILLED",  # STM simulates immediate fill
                "executedQty": request.quantity,
                "cummulativeQuoteQty": str(
                    float(request.quantity) * float(execution_price)
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "updateTime": datetime.now(timezone.utc).isoformat(),
            }

            # Save order
            orders = self._load_orders()
            orders.append(order_data)
            self._save_orders(orders)

            # Handle different order types
            if request.type == "MARKET":
                # Create new position for MARKET orders
                position_id = self._generate_id()
                position_data = {
                    "positionId": position_id,
                    "orderId": order_id,
                    "symbol": request.symbol,
                    "side": request.side,
                    "quantity": request.quantity,
                    "entryPrice": execution_price,
                    "leverage": 1,  # Default leverage
                    "isIsolated": request.isIsolated == "TRUE",
                    "status": "open",
                    "pnl": 0.0,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }

                # Save position
                positions = self._load_positions()
                positions.append(position_data)
                self._save_positions(positions)

                # Update account balance
                await self._update_account_balance(position_data, "opened")

                # Notify position change
                await self._notify_position_change("opened", position_data)

                return OrderResponse(
                    success=True,
                    orderId=order_id,
                    positionId=position_id,
                    executedPrice=execution_price,
                    executedQuantity=request.quantity,
                    message="Order executed successfully",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

            elif request.type in [
                "STOP_MARKET",
                "STOP_LOSS",
            ] or self._is_take_profit_order(request):
                # Handle SL/TP orders - find matching position using FIFO
                matching_position = await self._find_matching_position_fifo(
                    request.symbol, request.quantity, request.side
                )

                if not matching_position:
                    return OrderResponse(
                        success=False,
                        orderId=order_id,
                        message=f"No matching position found for {request.symbol} {request.quantity} {request.side}",
                    )

                # Associate order with position
                position_id = matching_position["positionId"]

                # Update position with SL/TP info
                positions = self._load_positions()
                for i, pos in enumerate(positions):
                    if pos["positionId"] == position_id:
                        if request.type in ["STOP_MARKET", "STOP_LOSS"]:
                            positions[i]["stopLossPrice"] = request.stopPrice
                            positions[i]["stopLossOrderId"] = order_id
                        elif self._is_take_profit_order(request):
                            positions[i]["takeProfitPrice"] = request.price
                            positions[i]["takeProfitOrderId"] = order_id
                        positions[i]["updatedAt"] = datetime.now(
                            timezone.utc
                        ).isoformat()
                        break

                self._save_positions(positions)

                # Notify position change
                await self._notify_position_change("updated", matching_position)

                order_type = (
                    "STOP_LOSS"
                    if request.type in ["STOP_MARKET", "STOP_LOSS"]
                    else "TAKE_PROFIT"
                )
                return OrderResponse(
                    success=True,
                    orderId=order_id,
                    positionId=position_id,
                    executedPrice=execution_price,
                    executedQuantity="0",  # Not filled yet
                    message=f"{order_type} order placed successfully",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            else:
                # For LIMIT orders, just return order confirmation
                return OrderResponse(
                    success=True,
                    orderId=order_id,
                    executedPrice=execution_price,
                    executedQuantity="0",  # Not filled yet
                    message="Order placed successfully",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

        except Exception as e:
            log.error(f"Error processing Binance margin order: {e}")
            return OrderResponse(
                success=False,
                orderId=self._generate_id(),
                message=f"Error processing order: {str(e)}",
            )

    async def open_position(self, request: OpenPositionRequest) -> OrderResponse:
        """Open a new position"""
        try:
            # Idempotency: if clientOrderId already used for an OPEN order, return existing
            if request.clientOrderId:
                try:
                    existing_orders = self._load_orders()
                    for o in existing_orders:
                        if (
                            o.get("type") == "OPEN"
                            and o.get("clientOrderId") == request.clientOrderId
                        ):
                            # Find existing position
                            position = await self.get_position(o.get("positionId", ""))
                            if position:
                                return OrderResponse(
                                    success=True,
                                    orderId=o.get("orderId", ""),
                                    positionId=o.get("positionId"),
                                    executedPrice=position.get("entryPrice"),
                                    executedQuantity=position.get("quantity"),
                                    stopLossOrderId=position.get("stopLossOrderId"),
                                    takeProfitOrderId=position.get("takeProfitOrderId"),
                                    message="Idempotent open: existing position returned",
                                )
                except Exception:
                    # If any issue reading orders, proceed to normal flow
                    pass

            # Generate IDs
            order_id = self._generate_id()
            position_id = self._generate_id()

            # Get current price
            current_price = self._get_current_price(request.symbol)

            # Validate request
            if request.type == "LIMIT" and not request.price:
                return OrderResponse(
                    success=False,
                    orderId=order_id,
                    message="Price required for LIMIT orders",
                )

            if request.type == "STOP_MARKET" and not request.stopPrice:
                return OrderResponse(
                    success=False,
                    orderId=order_id,
                    message="Stop price required for STOP_MARKET orders",
                )

            # Create position
            position = Position(
                positionId=position_id,
                orderId=order_id,
                botId=request.botId,
                strategy=request.strategy,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                entryPrice=str(current_price),
                leverage=request.leverage,
                isIsolated=request.isIsolated or False,
                stopLossPrice=(
                    self._parse_optional_price(request.stopLoss.price)
                    if request.stopLoss
                    else None
                ),
                takeProfitPrice=(
                    self._parse_optional_price(request.takeProfit.price)
                    if request.takeProfit
                    else None
                ),
                status="open",
            )

            # Generate SL/TP order IDs if configured
            sl_order_id = self._generate_id() if request.stopLoss else None
            tp_order_id = self._generate_id() if request.takeProfit else None

            position.stopLossOrderId = sl_order_id
            position.takeProfitOrderId = tp_order_id

            # Save position
            positions = self._load_positions()
            positions.append(position.dict())
            self._save_positions(positions)

            # Update account balance
            await self._update_account_balance(position.dict(), "opened")

            # Notify position change
            await self._notify_position_change("opened", position.dict())

            # Save order record
            orders = self._load_orders()
            order_record = {
                "orderId": order_id,
                "positionId": position_id,
                "type": "OPEN",
                "symbol": request.symbol,
                "side": request.side,
                "quantity": request.quantity,
                "price": str(current_price),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "clientOrderId": request.clientOrderId,
            }
            orders.append(order_record)
            self._save_orders(orders)

            log.info(
                f"Position opened: {position_id} for {request.symbol} {request.side} {request.quantity}"
            )

            return OrderResponse(
                success=True,
                orderId=order_id,
                positionId=position_id,
                executedPrice=str(current_price),
                executedQuantity=request.quantity,
                stopLossOrderId=sl_order_id,
                takeProfitOrderId=tp_order_id,
                message="Position opened successfully",
            )

        except Exception as e:
            log.error(f"Error opening position: {e}")
            return OrderResponse(
                success=False,
                orderId=self._generate_id(),
                message=f"Error opening position: {str(e)}",
            )

    async def close_position(self, request: ClosePositionRequest) -> OrderResponse:
        """Close an existing position"""
        try:
            # Load positions
            positions = self._load_positions()

            # Find position
            position_index = None
            for i, pos_data in enumerate(positions):
                if pos_data.get("positionId") == request.positionId:
                    position_index = i
                    break

            if position_index is None:
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message=f"Position {request.positionId} not found",
                )

            position_data = positions[position_index]

            # Check if position is already closed
            if position_data.get("status") != "open":
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message=f"Position {request.positionId} is already closed",
                )

            # Generate close order ID
            close_order_id = self._generate_id()

            # Get current price for P&L calculation
            current_price = self._get_current_price(position_data["symbol"])

            # Calculate final P&L
            entry_price = float(position_data["entryPrice"])
            quantity = float(position_data["quantity"])

            if position_data["side"] == "BUY":
                final_pnl = (current_price - entry_price) * quantity
            else:  # SELL
                final_pnl = (entry_price - current_price) * quantity

            # Update position
            position_data["status"] = "closed"
            position_data["closedAt"] = datetime.now(timezone.utc).isoformat()
            position_data["updatedAt"] = datetime.now(timezone.utc).isoformat()
            position_data["pnl"] = final_pnl

            # Save updated position
            positions[position_index] = position_data
            self._save_positions(positions)

            # Update account balance
            await self._update_account_balance(position_data, "closed")

            # Notify position change
            await self._notify_position_change("closed", position_data)

            # Save close order record
            orders = self._load_orders()
            close_order_record = {
                "orderId": close_order_id,
                "positionId": request.positionId,
                "type": "CLOSE",
                "symbol": position_data["symbol"],
                "side": (
                    "SELL" if position_data["side"] == "BUY" else "BUY"
                ),  # Opposite side
                "quantity": position_data["quantity"],
                "price": str(current_price),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "clientOrderId": request.clientOrderId,
                "reason": request.reason,
            }
            orders.append(close_order_record)
            self._save_orders(orders)

            log.info(f"Position closed: {request.positionId} with P&L: {final_pnl}")

            return OrderResponse(
                success=True,
                orderId=close_order_id,
                positionId=request.positionId,
                executedPrice=str(current_price),
                executedQuantity=position_data["quantity"],
                message=f"Position closed successfully. P&L: {final_pnl:.4f}",
            )

        except Exception as e:
            log.error(f"Error closing position: {e}")
            return OrderResponse(
                success=False,
                orderId=self._generate_id(),
                message=f"Error closing position: {str(e)}",
            )

    async def set_stop_loss(self, position_id: str, price: str) -> OrderResponse:
        """Attach or update a Stop Loss for a position (Binance-like: separate order)."""
        try:
            positions = self._load_positions()
            idx = next(
                (
                    i
                    for i, p in enumerate(positions)
                    if p.get("positionId") == position_id
                ),
                None,
            )
            if idx is None:
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message=f"Position {position_id} not found",
                )

            # Validate price numeric
            sl_price_str = self._parse_optional_price(price)
            if sl_price_str is None:
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message="Invalid stop loss price",
                )

            # Update position
            pos = positions[idx]
            sl_order_id = self._generate_id()
            pos["stopLossPrice"] = sl_price_str
            pos["stopLossOrderId"] = sl_order_id
            pos["updatedAt"] = datetime.now(timezone.utc).isoformat()
            positions[idx] = pos
            self._save_positions(positions)

            # Save order record
            orders = self._load_orders()
            orders.append(
                {
                    "orderId": sl_order_id,
                    "positionId": position_id,
                    "type": "STOP_LOSS",
                    "symbol": pos.get("symbol"),
                    "side": pos.get("side"),
                    "quantity": pos.get("quantity"),
                    "price": sl_price_str,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._save_orders(orders)

            # Notify position change
            await self._notify_position_change("updated", pos)

            return OrderResponse(
                success=True,
                orderId=sl_order_id,
                positionId=position_id,
                message="Stop loss set",
            )
        except Exception as e:
            log.error(f"Error setting stop loss: {e}")
            return OrderResponse(
                success=False,
                orderId=self._generate_id(),
                message=f"Error setting stop loss: {str(e)}",
            )

    async def set_take_profit(self, position_id: str, price: str) -> OrderResponse:
        """Attach or update a Take Profit for a position (Binance-like: separate order)."""
        try:
            positions = self._load_positions()
            idx = next(
                (
                    i
                    for i, p in enumerate(positions)
                    if p.get("positionId") == position_id
                ),
                None,
            )
            if idx is None:
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message=f"Position {position_id} not found",
                )

            tp_price_str = self._parse_optional_price(price)
            if tp_price_str is None:
                return OrderResponse(
                    success=False,
                    orderId=self._generate_id(),
                    message="Invalid take profit price",
                )

            pos = positions[idx]
            tp_order_id = self._generate_id()
            pos["takeProfitPrice"] = tp_price_str
            pos["takeProfitOrderId"] = tp_order_id
            pos["updatedAt"] = datetime.now(timezone.utc).isoformat()
            positions[idx] = pos
            self._save_positions(positions)

            orders = self._load_orders()
            orders.append(
                {
                    "orderId": tp_order_id,
                    "positionId": position_id,
                    "type": "TAKE_PROFIT",
                    "symbol": pos.get("symbol"),
                    "side": pos.get("side"),
                    "quantity": pos.get("quantity"),
                    "price": tp_price_str,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._save_orders(orders)

            await self._notify_position_change("updated", pos)

            return OrderResponse(
                success=True,
                orderId=tp_order_id,
                positionId=position_id,
                message="Take profit set",
            )
        except Exception as e:
            log.error(f"Error setting take profit: {e}")
            return OrderResponse(
                success=False,
                orderId=self._generate_id(),
                message=f"Error setting take profit: {str(e)}",
            )

    async def get_positions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all positions, optionally filtered by status"""
        positions = self._load_positions()

        # Update P&L for open positions
        updated_positions = []
        for position_data in positions:
            if position_data.get("status") == "open":
                position = Position(**position_data)
                updated_position = self._update_position_pnl(position)
                position_data.update(updated_position.dict())
            updated_positions.append(position_data)

        # Save updated positions (all positions, not filtered)
        self._save_positions(updated_positions)

        # Filter by status if specified (for return only)
        if status:
            filtered_positions = [
                p for p in updated_positions if p.get("status") == status
            ]
            return filtered_positions

        return updated_positions

    async def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific position by ID"""
        positions = self._load_positions()

        for position_data in positions:
            if position_data.get("positionId") == position_id:
                # Update P&L if position is open
                if position_data.get("status") == "open":
                    position = Position(**position_data)
                    updated_position = self._update_position_pnl(position)
                    position_data.update(updated_position.dict())
                    self._save_positions(positions)
                return position_data

        return None

    async def get_orders(
        self, position_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all orders, optionally filtered by position ID"""
        orders = self._load_orders()

        if position_id:
            orders = [o for o in orders if o.get("positionId") == position_id]

        return orders

    async def get_margin_account(self) -> Dict[str, Any]:
        """Get margin account info - Binance compatible"""
        try:
            if not self.account_service:
                return {"error": "Account service not available"}

            account = await self.account_service.get_account()
            return {
                "userAssets": [
                    {
                        "asset": "USDT",
                        "free": str(account.get("usdt_balance", 0)),
                        "locked": str(account.get("usdt_locked", 0)),
                        "borrowed": "0",
                        "interest": "0",
                        "netAsset": str(account.get("usdt_balance", 0)),
                    },
                    {
                        "asset": "DOGE",
                        "free": str(account.get("doge_balance", 0)),
                        "locked": str(account.get("doge_locked", 0)),
                        "borrowed": "0",
                        "interest": "0",
                        "netAsset": str(account.get("doge_balance", 0)),
                    },
                ],
                "totalAssetOfBtc": "0",
                "totalLiabilityOfBtc": "0",
                "totalNetAssetOfBtc": "0",
            }
        except Exception as e:
            log.error(f"Error getting margin account: {e}")
            return {"error": str(e)}

    async def get_margin_positions(self) -> List[Dict[str, Any]]:
        """Get margin positions - Binance compatible"""
        try:
            positions = self._load_positions()
            open_positions = [p for p in positions if p.get("status") == "open"]

            # Convert to Binance format
            binance_positions = []
            for pos in open_positions:
                binance_positions.append(
                    {
                        "symbol": pos.get("symbol"),
                        "initialMargin": "0",
                        "maintMargin": "0",
                        "unrealizedProfit": str(pos.get("pnl", 0)),
                        "positionInitialMargin": "0",
                        "openOrderInitialMargin": "0",
                        "leverage": str(pos.get("leverage", 1)),
                        "isolated": pos.get("isIsolated", False),
                        "entryPrice": pos.get("entryPrice"),
                        "maxNotional": "0",
                        "bidNotional": "0",
                        "askNotional": "0",
                        "positionSide": "BOTH",
                        "positionAmt": (
                            pos.get("quantity")
                            if pos.get("side") == "BUY"
                            else f"-{pos.get('quantity')}"
                        ),
                        "updateTime": pos.get("updatedAt", ""),
                    }
                )

            return binance_positions
        except Exception as e:
            log.error(f"Error getting margin positions: {e}")
            return []

    async def get_open_orders(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get open orders - Binance compatible"""
        try:
            orders = self._load_orders()

            # Filter by symbol if provided
            if symbol:
                orders = [o for o in orders if o.get("symbol") == symbol]

            # Filter only open orders (not filled)
            open_orders = [o for o in orders if o.get("status") != "FILLED"]

            return open_orders
        except Exception as e:
            log.error(f"Error getting open orders: {e}")
            return []

    def _is_take_profit_order(self, request: BinanceMarginOrderRequest) -> bool:
        """Detect if a LIMIT order is a Take Profit order (Binance compatible)"""
        # Take Profit: LIMIT order with side opposite to existing position
        if request.type != "LIMIT":
            return False

        # Check if there's a matching position with opposite side
        positions = self._load_positions()
        for pos in positions:
            if (
                pos.get("status") == "open"
                and pos.get("symbol") == request.symbol
                and pos.get("quantity") == request.quantity
            ):

                position_side = pos.get("side")
                # If order side is opposite to position side, it's a TP
                if (position_side == "BUY" and request.side == "SELL") or (
                    position_side == "SELL" and request.side == "BUY"
                ):
                    return True

        return False

    async def _find_matching_position_fifo(
        self, symbol: str, quantity: str, order_side: str
    ) -> Optional[Dict[str, Any]]:
        """Find matching position using FIFO (First In, First Out) - Binance compatible"""
        try:
            positions = self._load_positions()

            # Filter open positions with matching symbol and quantity
            matching_positions = []
            for pos in positions:
                if (
                    pos.get("status") == "open"
                    and pos.get("symbol") == symbol
                    and pos.get("quantity") == quantity
                ):

                    # Check if order side is opposite to position side
                    position_side = pos.get("side")
                    if (position_side == "BUY" and order_side == "SELL") or (
                        position_side == "SELL" and order_side == "BUY"
                    ):
                        matching_positions.append(pos)

            if not matching_positions:
                return None

            # Sort by creation time (FIFO - oldest first)
            matching_positions.sort(key=lambda x: x.get("createdAt", ""))

            # Return the oldest matching position
            oldest_position = matching_positions[0]
            log.info(
                f"FIFO matching: Found position {oldest_position['positionId']} for {symbol} {quantity} {order_side}"
            )

            return oldest_position

        except Exception as e:
            log.error(f"Error finding matching position: {e}")
            return None


def update_price(price: float) -> None:
    """Update the current price (called from Binance service)"""
    global _current_price
    _current_price = price
