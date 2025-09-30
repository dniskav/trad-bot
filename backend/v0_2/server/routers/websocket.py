import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from backend.shared.logger import get_logger
from ..services.websocket_manager import WebSocketManager
from ..services.stm_service import STMService

router = APIRouter(tags=["websocket"])
log = get_logger("server.websocket")

# Use singleton instances
ws_manager = WebSocketManager()
stm_service = STMService()

# In-memory cache to log PnL changes only when they actually change
_last_pnl_by_position: Dict[str, float] = {}

# Allowed mutable fields for "position_change" events
_ALLOWED_POSITION_FIELDS = {
    "entryPrice",
    "positionAmt",
    "unrealizedProfit",
    "leverage",
    "positionSide",
    "updateTime",
    "pnl",
    "current_price",
    "markPrice",
    "status",
}


def _sanitize_position_change(payload: dict) -> dict:
    """Whitelist and lightly normalize fields for position_change events."""
    sanitized = {
        "type": "position_change",
        "positionId": payload.get("positionId"),
        "ts": payload.get("ts"),
        "fields": {},
    }
    fields = payload.get("fields") or {}
    if not isinstance(fields, dict):
        return sanitized

    for key, value in fields.items():
        if key not in _ALLOWED_POSITION_FIELDS:
            continue
        # Normalize numeric fields to strings where our API typically returns strings
        if key in {"entryPrice", "positionAmt", "unrealizedProfit", "markPrice"}:
            try:
                sanitized["fields"][key] = f"{float(value)}"
            except Exception:
                # Skip invalid numeric values
                continue
        else:
            sanitized["fields"][key] = value

    return sanitized


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data broadcasting"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; we don't expect incoming messages
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@router.post("/ws/notify")
async def notify_websocket_clients(request: Request):
    """Receive notifications from STM and broadcast to WebSocket clients"""
    try:
        data = await request.json()
        log.info(f"Received notification: {data.get('type')}")

        # Normalize and broadcast to all clients
        # Expected payloads:
        # { type: 'position_change', positionId, fields: { ... }, ts }
        # { type: 'position_opened' | 'position_closed', positionId, ts }
        # { type: 'account_balance_update', data, ts }
        if data.get("type") == "position_change":
            data = _sanitize_position_change(data)
        await ws_manager.broadcast(data)

        # Handle different event types
        event_type = data.get("type")

        if event_type == "position_change":
            try:
                resp = await stm_service.get_positions(status="open")
                positions = resp.get("positions", []) or []

                for p in positions:
                    pid = p.get("positionId")
                    pnl = p.get("pnl")
                    if pid is None or pnl is None:
                        continue

                    last = _last_pnl_by_position.get(pid)
                    # Log only when PnL actually changes (allow tiny epsilon)
                    if last is None or abs(float(pnl) - float(last)) > 1e-8:
                        _last_pnl_by_position[pid] = float(pnl)
                        log.info(f"PNL change | position={pid} pnl={float(pnl):.8f}")
            except Exception as e:
                log.warning(f"Failed logging PnL changes: {e}")

        elif event_type == "position_opened" or event_type == "position_closed":
            # Trigger refetch on clients; nothing to compute here
            log.info(
                f"Position lifecycle event: {event_type} id={data.get('positionId')}"
            )

        elif event_type == "account_balance_update":
            # Normalize: fetch authoritative balance from STM and rebroadcast
            try:
                normalized = await stm_service.get_account_synth()
                payload = {"type": "account_balance_update", "data": normalized}
                await ws_manager.broadcast(payload)
                log.info("📊 Broadcasted normalized account_balance_update to clients")
            except Exception as e:
                log.error(f"Failed to normalize account update: {e}")

        elif event_type == "execution_report":
            # Log execution report details
            symbol = data.get("s", "unknown")
            side = data.get("S", "unknown")
            quantity = data.get("q", "0")
            price = data.get("L", "0")
            commission = data.get("n", "0")
            commission_asset = data.get("N", "USDT")
            log.info(
                f"Order executed | {symbol} {side} {quantity} @ {price} | Commission: {commission} {commission_asset}"
            )

        elif event_type == "account_position":
            # Log account position updates
            positions = data.get("P", [])
            balances = data.get("B", [])

            # Log balance information
            for balance in balances:
                asset = balance.get("a", "unknown")
                free = balance.get("f", "0")
                locked = balance.get("l", "0")
                log.info(f"Account balance | {asset}: Free={free}, Locked={locked}")

            # Log position information
            for pos in positions:
                symbol = pos.get("s", "unknown")
                position_amt = pos.get("pa", "0")
                unrealized_pnl = pos.get("up", "0")
                log.info(
                    f"Account position | {symbol}: {position_amt} | PnL: {unrealized_pnl}"
                )

            # Fetch and broadcast updated account balance to frontend
            try:
                account_response = await stm_service.get_account_synth()
                if account_response.get("success"):
                    account_data = account_response.get("data", {})
                    # Broadcast account balance update to frontend
                    balance_update = {
                        "type": "account_balance_update",
                        "data": account_data,
                    }
                    await ws_manager.broadcast(balance_update)
                    log.info("📊 Account balance update broadcasted to frontend")
            except Exception as e:
                log.error(f"Failed to fetch and broadcast account balance: {e}")

        return {"success": True, "message": "Notification broadcasted"}
    except Exception as e:
        log.error(f"Error processing notification: {e}")
        return {"success": False, "error": str(e)}
