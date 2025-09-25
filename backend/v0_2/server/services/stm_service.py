import asyncio
import json
import urllib.request
import urllib.error
import websockets
from datetime import datetime, timezone
from backend.shared.logger import get_logger

log = get_logger("server.stm_service")

STM_HTTP = "http://127.0.0.1:8100"
STM_WS = "ws://127.0.0.1:8100/ws"


class STMService:
    """Handles communication with STM (Synthetic Trading Manager)"""

    def __init__(self) -> None:
        self.stm_log_enabled = False

    async def check_health(self) -> bool:
        """Check if STM service is healthy"""
        try:
            with urllib.request.urlopen(f"{STM_HTTP}/health", timeout=5) as resp:
                if resp.status != 200:
                    return False
                data = json.loads(resp.read().decode())
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
            with urllib.request.urlopen(
                f"{STM_HTTP}/socket/logging", timeout=5
            ) as resp:
                data = resp.read().decode()
                stm_state = json.loads(data)
                stm_state["server_binance_enabled"] = self.stm_log_enabled
                return stm_state
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": str(e), "code": e.code}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def set_socket_logging_state(self, payload: dict) -> dict:
        """Set socket logging state in STM"""
        try:
            scope = str(payload.get("scope", "all")).lower()
            if scope == "binance":
                if isinstance(payload.get("enabled"), bool):
                    self.stm_log_enabled = payload["enabled"]
                    log.info(
                        f"🛠️  (server) Binance socket logging: {'on' if self.stm_log_enabled else 'off'}"
                    )

            req = urllib.request.Request(
                f"{STM_HTTP}/socket/logging",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode()
                stm_resp = json.loads(data)
                stm_resp["server_binance_enabled"] = self.stm_log_enabled
                return stm_resp
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": str(e), "code": e.code}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def get_account_synth(self) -> dict:
        """Get synthetic account data from STM"""
        try:
            with urllib.request.urlopen(f"{STM_HTTP}/account/synth", timeout=5) as resp:
                data = resp.read().decode()
                return json.loads(data)
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": str(e), "code": e.code}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}

    async def reset_account_synth(self) -> dict:
        """Reset synthetic account via STM"""
        try:
            req = urllib.request.Request(
                f"{STM_HTTP}/account/synth/reset",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode()
                return json.loads(data)
        except urllib.error.HTTPError as e:
            return {"status": "error", "message": str(e), "code": e.code}
        except Exception as e:
            return {"status": "error", "message": str(e), "code": 500}
