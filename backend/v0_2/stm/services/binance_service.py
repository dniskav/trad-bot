import asyncio
import json
import websockets
from backend.shared.logger import get_logger
from backend.shared.settings import env_str
from services.account_service import update_price

log = get_logger("stm.binance_service")
SYMBOL = env_str("STM_SYMBOL", "dogeusdt").lower()
BINANCE_LOG_ENABLED = False


class BinanceService:
    def __init__(self):
        self.symbol = SYMBOL
        self.log_enabled = BINANCE_LOG_ENABLED

    async def bookticker_loop(self) -> None:
        """Connect to Binance WebSocket and track price updates"""
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@bookTicker"
        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    log.info(
                        f"🔌 Conectado a Binance bookTicker: {self.symbol.upper()}"
                    )
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            bid = data.get("b")
                            ask = data.get("a")
                            if bid is not None and ask is not None and self.log_enabled:
                                log.info(f"📈 {self.symbol.upper()} b={bid} a={ask}")
                            # Guardar último precio medio para cálculos de síntesis
                            try:
                                b = float(data.get("b"))
                                a = float(data.get("a"))
                                mid = (a + b) / 2.0
                                update_price(mid)
                            except Exception:
                                pass
                        except Exception:
                            continue
            except Exception as e:
                log.warning(f"⚠️  WS Binance desconectado: {e}. Reintentando...")
                await asyncio.sleep(2)

    def set_logging(self, enabled: bool) -> None:
        """Enable/disable Binance logging"""
        global BINANCE_LOG_ENABLED
        BINANCE_LOG_ENABLED = enabled
        self.log_enabled = enabled
