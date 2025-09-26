from typing import Optional, List
from fastapi import APIRouter, HTTPException
from backend.shared.logger import get_logger
from ..models.position import (
    BinanceMarginOrderRequest,
    OpenPositionRequest,
    ClosePositionRequest,
    OrderResponse,
)
from fastapi import Body

router = APIRouter(prefix="/sapi/v1/margin", tags=["margin"])
log = get_logger("stm.positions")

# Position service will be injected from app.py
position_service = None


def set_position_service(service):
    """Set the position service instance from app.py"""
    global position_service
    position_service = service


@router.post("/order", response_model=OrderResponse)
async def margin_order(request: BinanceMarginOrderRequest):
    """Binance Margin Order - exact endpoint from Binance API"""
    log.info(
        f"Binance margin order: {request.symbol} {request.side} {request.type} {request.quantity}"
    )
    return await position_service.binance_margin_order(request)


@router.post("/open", response_model=OrderResponse)
async def open_position(request: OpenPositionRequest):
    """Open a new position - simplified format for bots/frontend"""
    log.info(f"Opening position: {request.symbol} {request.side} {request.quantity}")
    return await position_service.open_position(request)


@router.post("/close", response_model=OrderResponse)
async def close_position(request: ClosePositionRequest):
    """Close an existing position manually"""
    log.info(f"Closing position: {request.positionId}")
    return await position_service.close_position(request)


@router.get("/")
async def get_positions(status: Optional[str] = None):
    """Get all positions, optionally filtered by status (open, closed, stopped, profited)"""
    log.info(f"Getting positions with status filter: {status}")
    positions = await position_service.get_positions(status)
    return {"success": True, "positions": positions, "count": len(positions)}


@router.get("/account")
async def get_margin_account():
    """Get margin account info - Binance compatible endpoint"""
    log.info("Getting margin account info")
    account_info = await position_service.get_margin_account()
    return account_info


@router.get("/positions")
async def get_margin_positions():
    """Get margin positions - Binance compatible endpoint"""
    log.info("Getting margin positions")
    positions = await position_service.get_margin_positions()
    return positions


@router.get("/openOrders")
async def get_open_orders(symbol: Optional[str] = None):
    """Get open orders - Binance compatible endpoint"""
    log.info(f"Getting open orders for symbol: {symbol}")
    orders = await position_service.get_open_orders(symbol)
    return orders


# STM-specific endpoints for testing
@router.post("/admin/reset")
async def admin_reset_positions_orders():
    """Clear all synthetic positions and orders (testing utility)."""
    if position_service is None:
        raise HTTPException(status_code=500, detail="PositionService not initialized")
    log.warning("Admin reset: clearing positions and orders (STM)")
    result = await position_service.reset_positions_and_orders()
    return {"success": True, **result}
