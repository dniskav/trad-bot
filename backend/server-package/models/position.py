from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class StopLossConfig(BaseModel):
    """Stop Loss configuration"""

    price: str = Field(..., description="Stop loss price")
    type: Literal["STOP_MARKET"] = "STOP_MARKET"


class TakeProfitConfig(BaseModel):
    """Take Profit configuration"""

    price: str = Field(..., description="Take profit price")
    type: Literal["LIMIT"] = "LIMIT"


class OpenPositionRequest(BaseModel):
    """Request model for opening a position - compatible with Binance format"""

    # Bot identification (optional, for STM tracking)
    botId: Optional[str] = Field(None, description="Bot identifier")
    strategy: Optional[str] = Field(None, description="Trading strategy name")

    # Core order parameters (Binance compatible)
    symbol: str = Field(..., description="Trading pair symbol (e.g., DOGEUSDT)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    type: Literal["MARKET", "LIMIT", "STOP_MARKET"] = Field(
        ..., description="Order type"
    )
    quantity: str = Field(..., description="Order quantity")
    leverage: Optional[int] = Field(None, description="Leverage (1-10)")
    isIsolated: Optional[bool] = Field(False, description="Isolated margin")

    # Price parameters (conditional on order type)
    price: Optional[str] = Field(None, description="Order price (for LIMIT orders)")
    stopPrice: Optional[str] = Field(None, description="Stop price (for STOP orders)")

    # Risk management
    stopLoss: Optional[StopLossConfig] = Field(
        None, description="Stop loss configuration"
    )
    takeProfit: Optional[TakeProfitConfig] = Field(
        None, description="Take profit configuration"
    )

    # Binance metadata
    clientOrderId: Optional[str] = Field(None, description="Client order ID")
    timeInForce: Optional[Literal["GTC", "IOC", "FOK"]] = Field(
        "GTC", description="Time in force"
    )
    timestamp: Optional[int] = Field(None, description="Order timestamp")


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
