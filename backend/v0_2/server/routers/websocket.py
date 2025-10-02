import asyncio
from typing import Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends
from backend.shared.logger import get_logger
from ..websocket_service_integration import websocket_service_dependency
from ..services.stm_service import STMService

router = APIRouter(tags=["websocket"])
log = get_logger("server.websocket")

# STM Service legacy
stm_service = STMService()

# In-memory cache to log PnL changes only when they actually change
_last_pnl_by_position: Dict[str, float] = {}

# Función helper para obtener servicio WebSocket con fallback
async def get_websocket_service():
    """Obtener servicio WebSocket hexagonal o legacy como fallback"""
    try:
        # Intentar obtener servicio hexagonal
        from ..websocket_service_integration import websocket_service_factory
        service = await websocket_service_factory()
        
        # Verificar si es el servicio hexagonal (WebSocketAdapter compatible)
        if hasattr(service, "connect") and hasattr(service, "broadcast"):
            log.info("Using Hexagonal WebSocket Service")
            return service
        else:
            # Es el servicio hexagonal, crear adapter
            from ..infrastructure.adapters.communication.websocket_service import WebSocketServiceAdapter
            adapter = WebSocketServiceAdapter(service)
            log.info("Using Hexagonal WebSocket Service (via adapter)")
            return adapter
            
    except Exception as e:
        log.warning(f"Hexagonal WebSocket service not available, using legacy singleton: {e}")
        # Fallback a servicio legacy
        from ..services.websocket_manager import WebSocketManager
        return WebSocketManager()

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
    ws_service = await get_websocket_service()
    
    # Conectar cliente
    client_id = await ws_service.connect(websocket)
    log.info(f"WebSocket client connected: {client_id}")
    
    try:
        while True:
            # Keep connection alive; we don't expect incoming messages
            await asyncio.sleep(60)
    except WebSocketDisconnect:
        await ws_service.disconnect(websocket)
        log.info(f"WebSocket client disconnected: {client_id}")


@router.post("/ws/notify")
async def notify_websocket_clients(request: Request):
    """Receive notifications from STM and broadcast to WebSocket clients"""
    try:
        data = await request.json()
        log.info(f"Received notification: {data.get('type')}")

        # Obtener servicio WebSocket con fallback
        ws_service = await get_websocket_service()

        # Normalize and broadcast to all clients
        # Expected payloads:
        # { type: 'position_change', positionId, fields: { ... }, ts }
        # { type: 'position_opened' | 'position_closed', positionId, ts }
        # { type: 'account_balance_update', data, ts }
        if data.get("type") == "position_change":
            data = _sanitize_position_change(data)
        await ws_service.broadcast(data)

        # Handle different event types
        event_type = data.get("type")

        if event_type == "position_change":
            try:
                resp = await stm_service.get_positions(status="open")
                positions = resp.get("positions", []) or []
                # Fetch current price once to approximate close fee and real-time PnL
                acct = await stm_service.get_account_synth()
                curr_price = (
                    float(acct.get("doge_price", 0)) if isinstance(acct, dict) else 0.0
                )
                # Fee rates (approx taker on entry and exit)
                TAKER = 0.0004

                for p in positions:
                    pid = p.get("positionId")
                    pnl = p.get("pnl")
                    if pid is None or pnl is None:
                        continue

                    # Compute net PnL after estimated fees
                    try:
                        entry = float(p.get("entryPrice", 0))
                        qty = float(p.get("quantity", 0)) or abs(
                            float(p.get("positionAmt", 0))
                        )
                        side = (
                            p.get("side")
                            or p.get("positionSide")
                            or ("SELL" if float(p.get("positionAmt", 0)) < 0 else "BUY")
                        ).upper()
                        gross = float(pnl)
                        # Estimate taker fees at entry and potential exit
                        fee_open = TAKER * entry * qty
                        fee_close = TAKER * (curr_price or entry) * qty
                        pnl_net = gross - fee_open - fee_close
                        # Broadcast pnl update for this position
                        await ws_service.broadcast(
                            {
                                "type": "position_change",
                                "positionId": pid,
                                "fields": {"pnl": f"{pnl_net}"},
                            }
                        )
                    except Exception:
                        pass

                    last = _last_pnl_by_position.get(pid)
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
                await ws_service.broadcast(payload)
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
                    await ws_service.broadcast(balance_update)
                    log.info("📊 Account balance update broadcasted to frontend")
            except Exception as e:
                log.error(f"Failed to fetch and broadcast account balance: {e}")

        return {"success": True, "message": "Notification broadcasted"}
    except Exception as e:
        log.error(f"Error processing notification: {e}")
        return {"success": False, "error": str(e)}


@router.get("/ws/status")
async def websocket_service_status():
    """Estado del servicio WebSocket (hexagonal o legacy)"""
    try:
        ws_service = await get_websocket_service()
        
        # Intentar obtener status si es servicio hexagonal
        if hasattr(ws_service, "get_service_status"):
            status = await ws_service.get_service_status()
            service_type = "Hexagonal WebSocket Service"
        else:
            # Servicio legacy
            status = {
                "service_status": "legacy",
                "active_connections": len(ws_service.connections),
                "service_type": "Legacy WebSocketManager (singleton)"
            }
            service_type = "Legacy WebSocket Manager"
        
        return {
            "status": "success",
            "service_type": service_type,
            "data": status
        }
        
    except Exception as e:
        log.error(f"Error getting WebSocket service status: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
