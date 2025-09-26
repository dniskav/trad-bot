from typing import Optional
from fastapi import APIRouter, HTTPException
import asyncio
from backend.shared.logger import get_logger
from ..services.stm_service import STMService
from ..models.position import OpenPositionRequest, ClosePositionRequest, OrderResponse
from fastapi import Body
import json
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/positions", tags=["positions"])
log = get_logger("server.positions")
stm_service = STMService()


async def _orchestrate_open_async(req: OpenPositionRequest) -> None:
    """Background task: open position and set SL/TP, then rely on STM -> Server WS notify."""
    try:
        # Check if position already exists (idempotency)
        if req.clientOrderId:
            existing_positions = await stm_service.get_positions(status="open")
            if existing_positions.get("success"):
                for pos in existing_positions.get("positions", []):
                    if pos.get("orderId") == req.clientOrderId:
                        log.info(
                            f"Position with clientOrderId {req.clientOrderId} already exists, skipping background creation"
                        )
                        return

        open_resp = await stm_service.open_position(req)
        if not open_resp.success or not open_resp.positionId:
            log.warning(f"Background open failed: {open_resp.message}")
            return
        pid = open_resp.positionId
        if req.stopLoss and req.stopLoss.price:
            await stm_service.set_stop_loss(pid, req.stopLoss.price)
        if req.takeProfit and req.takeProfit.price:
            await stm_service.set_take_profit(pid, req.takeProfit.price)
        log.info(f"Background open orchestrated OK for position {pid}")
    except Exception as e:
        log.warning(f"Background open error: {e}")


async def _orchestrate_sl_tp_async(position_id: str, req: OpenPositionRequest) -> None:
    """Background task: set SL/TP for an existing position."""
    print(f"🚀 BACKGROUND TASK STARTED for position {position_id}")
    log.info(f"Starting background SL/TP task for position {position_id}")
    try:
        print(f"📋 Request details: SL={req.stopLoss}, TP={req.takeProfit}")

        if req.stopLoss and req.stopLoss.price:
            print(f"🛑 Setting SL at {req.stopLoss.price} for position {position_id}")
            log.info(f"Setting SL at {req.stopLoss.price} for position {position_id}")
            sl_result = await stm_service.set_stop_loss(position_id, req.stopLoss.price)
            print(f"🛑 SL result: {sl_result}")
            log.info(f"SL result: {sl_result}")

        if req.takeProfit and req.takeProfit.price:
            print(f"🎯 Setting TP at {req.takeProfit.price} for position {position_id}")
            log.info(f"Setting TP at {req.takeProfit.price} for position {position_id}")
            tp_result = await stm_service.set_take_profit(
                position_id, req.takeProfit.price
            )
            print(f"🎯 TP result: {tp_result}")
            log.info(f"TP result: {tp_result}")

        print(f"✅ BACKGROUND TASK COMPLETED for position {position_id}")
        log.info(f"Background SL/TP task completed for position {position_id}")
    except Exception as e:
        print(f"❌ BACKGROUND TASK ERROR for position {position_id}: {e}")
        log.error(f"Background SL/TP error for position {position_id}: {e}")
        import traceback

        print(f"❌ Traceback: {traceback.format_exc()}")
        log.error(f"Traceback: {traceback.format_exc()}")


@router.post("/open", response_model=OrderResponse)
async def open_position(request: OpenPositionRequest):
    """Open a new position and, if provided, orchestrate SL/TP creation (Binance-like)."""
    log.info(
        f"Orchestrating position open: {request.symbol} {request.side} {request.quantity}"
    )

    # Ensure clientOrderId for idempotency
    if not request.clientOrderId:
        request.clientOrderId = f"srv-{uuid.uuid4().hex[:16]}"

    # Quick health check (max 1s total)
    healthy = False
    try:
        healthy = await asyncio.wait_for(stm_service.check_health(), timeout=1.0)
    except asyncio.TimeoutError:
        healthy = False

    if not healthy:
        # STM not available - respond immediately and process in background
        asyncio.create_task(_orchestrate_open_async(request))
        return OrderResponse(
            success=True,
            orderId=request.clientOrderId,
            message="Accepted: opening in background; you will be notified via WS",
        )

    # STM is healthy - try to open synchronously with short timeout
    try:
        # Use asyncio.wait_for to limit the timeout to 3 seconds
        open_resp = await asyncio.wait_for(
            stm_service.open_position(request), timeout=3.0
        )

        if not open_resp.success or not open_resp.positionId:
            # STM responded but failed - fallback to background
            asyncio.create_task(_orchestrate_open_async(request))
            return OrderResponse(
                success=True,
                orderId=request.clientOrderId,
                message="Accepted: STM failed, retrying in background; you will be notified via WS",
            )

        # Success - respond immediately to client, then process SL/TP in background
        position_id = open_resp.positionId

        # Start background task for SL/TP
        log.info(f"Starting background SL/TP task for position {position_id}")
        task = asyncio.create_task(_orchestrate_sl_tp_async(position_id, request))
        log.info(f"Background task created: {task}")

        # Return immediate response
        return open_resp

    except asyncio.TimeoutError:
        # STM is slow - respond immediately and process in background
        asyncio.create_task(_orchestrate_open_async(request))
        return OrderResponse(
            success=True,
            orderId=request.clientOrderId,
            message="Accepted: STM slow, opening in background; you will be notified via WS",
        )


@router.post("/close", response_model=OrderResponse)
async def close_position(request: ClosePositionRequest):
    """Close an existing position - proxy to STM"""
    log.info(f"Proxying position close request: {request.positionId}")
    return await stm_service.close_position(request)


@router.get("/")
async def get_positions(status: Optional[str] = None):
    """Get all positions - proxy to STM"""
    log.info(f"Proxying get positions request with status filter: {status}")
    return await stm_service.get_positions(status)


@router.get("/{position_id}")
async def get_position(position_id: str):
    """Get a specific position - proxy to STM"""
    log.info(f"Proxying get position request: {position_id}")
    return await stm_service.get_position(position_id)


@router.get("/{position_id}/orders")
async def get_position_orders(position_id: str):
    """Get orders for a position - proxy to STM"""
    log.info(f"Proxying get position orders request: {position_id}")
    return await stm_service.get_position_orders(position_id)


@router.get("/orders/all")
async def get_all_orders():
    """Get all orders - proxy to STM"""
    log.info("Proxying get all orders request")
    return await stm_service.get_all_orders()


@router.post("/admin/reset")
async def reset_all_data():
    """Reset/clear all positions and orders - proxy to STM"""
    log.info("Proxying reset positions/orders request")
    return await stm_service.reset_positions_orders()


@router.post("/{position_id}/orders/stop_loss", response_model=OrderResponse)
async def set_stop_loss(position_id: str, payload: dict = Body(...)):
    """Proxy to STM: create/update Stop Loss for a position"""
    try:
        price = payload.get("price")
        req = urllib.request.Request(
            f"http://127.0.0.1:8100/positions/{position_id}/orders/stop_loss",
            data=json.dumps({"price": price}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return OrderResponse(**data)
    except Exception as e:
        return OrderResponse(
            success=False, orderId="", message=f"Proxy error: {str(e)}"
        )


@router.post("/{position_id}/orders/take_profit", response_model=OrderResponse)
async def set_take_profit(position_id: str, payload: dict = Body(...)):
    """Proxy to STM: create/update Take Profit for a position"""
    try:
        price = payload.get("price")
        req = urllib.request.Request(
            f"http://127.0.0.1:8100/positions/{position_id}/orders/take_profit",
            data=json.dumps({"price": price}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return OrderResponse(**data)
    except Exception as e:
        return OrderResponse(
            success=False, orderId="", message=f"Proxy error: {str(e)}"
        )
