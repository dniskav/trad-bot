import asyncio
from typing import List
from fastapi import WebSocket
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))
from shared.logger import get_logger

log = get_logger("server.websocket_manager")


class WebSocketManager:
    """Manages WebSocket connections for the server"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.connections: List[WebSocket] = []
        self._initialized = True

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and track a new WebSocket connection"""
        await websocket.accept()
        self.connections.append(websocket)
        log.info(f"WS client connected (total: {len(self.connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        try:
            self.connections.remove(websocket)
            log.info(f"WS client disconnected (total: {len(self.connections)})")
        except ValueError:
            pass

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients"""
        if not self.connections:
            return

        disconnected = []
        for connection in self.connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                log.warning(f"Error broadcasting to WS client: {type(e).__name__}: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
