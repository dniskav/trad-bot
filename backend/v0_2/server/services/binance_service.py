import asyncio
import json
import ssl
import websockets
import aiohttp
from backend.shared.logger import get_logger
from backend.shared.settings import env_str
from .websocket_manager import WebSocketManager

log = get_logger("server.binance_service")
SYMBOL = env_str("SERVER_SYMBOL", "dogeusdt").lower()


class BinanceService:
    """Handles Binance WebSocket connections and data processing"""

    def __init__(self, ws_manager: WebSocketManager) -> None:
        self.ws_manager = ws_manager
        self.binance_log_enabled = False
        self.strategy_service = None  # Will be injected by strategy service

    async def bookticker_loop(self) -> None:
        """Connect to Binance bookTicker WebSocket and broadcast data"""
        url = f"wss://stream.binance.com:9443/ws/{SYMBOL}@bookTicker"

        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                async with websockets.connect(
                    url, ping_interval=20, ssl=ssl_context
                ) as ws:
                    log.info(
                        f"🔌 (server) Conectado a Binance bookTicker: {SYMBOL.upper()}"
                    )

                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            payload = {
                                "type": "bookTicker",
                                "symbol": SYMBOL.upper(),
                                "bid": data.get("b"),
                                "ask": data.get("a"),
                                "ts": data.get("E"),
                            }
                            await self.ws_manager.broadcast(payload)

                            if self.binance_log_enabled:
                                log.info(
                                    f"📈 (server) {SYMBOL.upper()} b={payload['bid']} a={payload['ask']}"
                                )
                        except Exception as e:
                            log.error(f"Error processing bookTicker data: {e}")
                            continue

            except Exception as e:
                log.warning(
                    f"⚠️  (server) Binance bookTicker desconectado: {e}. retry 2s"
                )
                await asyncio.sleep(2)

    async def kline_loop(self, interval: str = "1m") -> None:
        """Connect to Binance kline WebSocket and broadcast data"""
        url = f"wss://stream.binance.com:9443/ws/{SYMBOL}@kline_{interval}"

        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        while True:
            try:
                async with websockets.connect(
                    url, ping_interval=20, ssl=ssl_context
                ) as ws:
                    log.info(
                        f"🔌 (server) Conectado a Binance kline {interval}: {SYMBOL.upper()}"
                    )

                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            k = data.get("k", {})
                            payload = {
                                "type": "kline",
                                "symbol": SYMBOL.upper(),
                                "interval": interval,
                                "kline": {
                                    "o": k.get("o"),
                                    "h": k.get("h"),
                                    "l": k.get("l"),
                                    "c": k.get("c"),
                                    "v": k.get("v"),
                                    "t": k.get("t"),
                                    "T": k.get("T"),
                                    "closed": bool(k.get("x")),
                                },
                                "ts": data.get("E"),
                            }
                            await self.ws_manager.broadcast(payload)

                            # Forward kline data to strategy service for real-time updates
                            if (
                                hasattr(self, "strategy_service")
                                and self.strategy_service
                            ):
                                self.strategy_service.handle_websocket_kline_data(
                                    payload
                                )

                            if self.binance_log_enabled and payload["kline"]["closed"]:
                                log.info(
                                    f"🕯️  (server) kline {interval} close o={k.get('o')} c={k.get('c')}"
                                )
                        except Exception as e:
                            log.error(f"Error processing kline data: {e}")
                            continue

            except Exception as e:
                log.warning(f"⚠️  (server) Binance kline desconectado: {e}. retry 2s")
                await asyncio.sleep(2)

    async def get_historical_klines(
        self, interval: str = "1m", limit: int = 1000
    ) -> list:
        """Fetch historical klines from Binance REST API"""
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": SYMBOL.upper(), "interval": interval, "limit": limit}

        # Create SSL context that doesn't verify certificates (same as WebSocket)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        try:
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        log.info(
                            f"📊 Fetched {len(data)} historical klines for {SYMBOL.upper()}"
                        )
                        return data
                    else:
                        log.error(f"Failed to fetch klines: {response.status}")
                        return []
        except Exception as e:
            log.error(f"Error fetching historical klines: {e}")
            return []

    def set_logging_enabled(self, enabled: bool) -> None:
        """Enable or disable Binance logging"""
        self.binance_log_enabled = enabled
        log.info(f"🛠️  (server) Binance socket logging: {'on' if enabled else 'off'}")
