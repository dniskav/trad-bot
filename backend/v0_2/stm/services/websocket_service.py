import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from backend.shared.logger import get_logger
from ..services.account_service import update_price

log = get_logger("stm.websocket_service")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("WS client connected")

    def disconnect(self, websocket: WebSocket) -> None:
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass
        log.info("WS client disconnected")

    async def broadcast(self, message: dict) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


class WebSocketService:
    def __init__(self):
        self.manager = ConnectionManager()

    async def send_test_message(self, payload: Optional[dict] = None) -> dict:
        """Send a test message via WebSocket to all connected clients"""
        msg = {
            "type": "test_message",
            "message": "hello from STM",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if isinstance(payload, dict):
            msg.update({k: v for k, v in payload.items() if k not in ("type",)})
        await self.manager.broadcast(msg)
        log.info("📤 Test message broadcasted to WS clients")
        return {"status": "sent", "payload": msg}

    async def handle_connection(self, websocket: WebSocket) -> None:
        """Handle WebSocket connection"""
        await self.manager.connect(websocket)
        try:
            # Send initial hello
            await websocket.send_json(
                {
                    "type": "stm_hello",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            while True:
                # Wait with timeout for inbound ping or messages
                try:
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Periodic server heartbeat
                    await websocket.send_json(
                        {
                            "type": "stm_heartbeat",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    continue

                if not isinstance(msg, dict):
                    continue

                msg_type = str(msg.get("type", "")).lower()
                if msg_type == "ping":
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                else:
                    # Echo unknown messages for now
                    await websocket.send_json(
                        {
                            "type": "echo",
                            "payload": msg,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        except WebSocketDisconnect:
            self.manager.disconnect(websocket)
        except Exception as e:
            self.manager.disconnect(websocket)
            try:
                await websocket.close()
            except Exception:
                pass
