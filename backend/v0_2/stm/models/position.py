from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class BinanceMarginOrderRequest(BaseModel):
    """Binance Margin Order Request - exact format from Binance API"""

    symbol: str = Field(..., description="Trading pair symbol (e.g., DOGEUSDT)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    type: Literal["MARKET", "LIMIT", "STOP_MARKET", "STOP_LOSS", "TAKE_PROFIT"] = Field(
        ..., description="Order type"
    )
    quantity: str = Field(..., description="Order quantity")
    price: Optional[str] = Field(None, description="Order price (for LIMIT orders)")
    stopPrice: Optional[str] = Field(None, description="Stop price (for STOP orders)")
    timeInForce: Optional[Literal["GTC", "IOC", "FOK"]] = Field(
        "GTC", description="Time in force"
    )
    newOrderRespType: Optional[Literal["ACK", "RESULT", "FULL"]] = Field(
        "RESULT", description="Response type"
    )
    sideEffectType: Optional[Literal["NO_SIDE_EFFECT", "MARGIN_BUY", "AUTO_REPAY"]] = (
        Field("NO_SIDE_EFFECT", description="Side effect type")
    )
    isIsolated: Optional[Literal["TRUE", "FALSE"]] = Field(
        "FALSE", description="Isolated margin"
    )
    newClientOrderId: Optional[str] = Field(None, description="Client order ID")
    icebergQty: Optional[str] = Field(None, description="Iceberg quantity")
    recvWindow: Optional[int] = Field(5000, description="Receive window")
    timestamp: Optional[int] = Field(None, description="Order timestamp")


class OpenPositionRequest(BaseModel):
    """Request model for opening a position - simplified format for bots/frontend"""

    # Bot identification (optional, for STM tracking)
    botId: Optional[str] = Field(None, description="Bot identifier")
    strategy: Optional[str] = Field(None, description="Trading strategy name")

    # Core order parameters
    symbol: str = Field(..., description="Trading pair symbol (e.g., DOGEUSDT)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    quantity: str = Field(..., description="Order quantity")
    leverage: Optional[int] = Field(None, description="Leverage (1-10)")
    isIsolated: Optional[bool] = Field(False, description="Isolated margin")

    # Risk management (optional)
    stopLossPrice: Optional[str] = Field(None, description="Stop loss price")
    takeProfitPrice: Optional[str] = Field(None, description="Take profit price")

    # Binance metadata
    clientOrderId: Optional[str] = Field(None, description="Client order ID")


class ClosePositionRequest(BaseModel):
    """Request model for closing a position"""

    positionId: str = Field(..., description="Position ID to close")
    reason: Optional[str] = Field("manual", description="Close reason")
    clientOrderId: Optional[str] = Field(None, description="Client order ID")


class OrderResponse(BaseModel):
    """Response model for order operations"""

    success: bool = Field(..., description="Operation success")
    orderId: str = Field(..., description="Generated order ID")
    positionId: Optional[str] = Field(None, description="Position ID (for open orders)")
    executedPrice: Optional[str] = Field(None, description="Execution price")
    executedQuantity: Optional[str] = Field(None, description="Executed quantity")
    stopLossOrderId: Optional[str] = Field(None, description="Stop loss order ID")
    takeProfitOrderId: Optional[str] = Field(None, description="Take profit order ID")
    message: str = Field(..., description="Response message")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Position(BaseModel):
    """Position model for internal tracking"""

    positionId: str = Field(..., description="Unique position ID")
    orderId: str = Field(..., description="Original order ID")
    botId: Optional[str] = Field(None, description="Bot identifier")
    strategy: Optional[str] = Field(None, description="Strategy name")
    symbol: str = Field(..., description="Trading pair")
    side: Literal["BUY", "SELL"] = Field(..., description="Position side")
    quantity: str = Field(..., description="Position quantity")
    entryPrice: str = Field(..., description="Entry price")
    leverage: Optional[int] = Field(None, description="Leverage used")
    isIsolated: bool = Field(False, description="Isolated margin")

    # Risk management
    stopLossPrice: Optional[str] = Field(None, description="Stop loss price")
    takeProfitPrice: Optional[str] = Field(None, description="Take profit price")
    stopLossOrderId: Optional[str] = Field(None, description="Stop loss order ID")
    takeProfitOrderId: Optional[str] = Field(None, description="Take profit order ID")

    # Status
    status: Literal["open", "closed", "stopped", "profited"] = Field(
        "open", description="Position status"
    )
    pnl: float = Field(0.0, description="Current P&L")

    # Timestamps
    createdAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updatedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    closedAt: Optional[str] = Field(None, description="Close timestamp")
