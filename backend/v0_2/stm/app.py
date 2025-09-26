import asyncio
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.shared.logger import get_logger
from backend.shared.settings import env_str

# Import routers
from .routers import health, account, socket, websocket, positions
from .services.account_service import AccountService
from .services.binance_service import BinanceService
from .services.position_service import PositionService
from .services.price_monitor import PriceMonitor
from .middlewares.logging import log_requests_middleware

log = get_logger("stm.v0.2")

# Server URL for notifications
SERVER_URL = "http://localhost:8200"


async def notify_server_position_change(change_type: str, position_data: dict):
    """Notify the main server about position changes"""
    try:
        log.info(
            f"🔔 Sending position change notification: {change_type} for position {position_data.get('positionId', 'unknown')}"
        )
        async with aiohttp.ClientSession() as session:
            payload = {
                "type": "position_change",
                "change_type": change_type,
                "position": position_data,
            }
            async with session.post(
                f"{SERVER_URL}/ws/notify", json=payload
            ) as response:
                if response.status == 200:
                    log.info(
                        f"✅ Position change notification sent successfully: {change_type}"
                    )
                else:
                    log.warning(f"❌ Failed to notify server: {response.status}")
    except Exception as e:
        log.error(f"💥 Error notifying server: {e}")


# Initialize services
account_service = AccountService()
position_service = PositionService(
    on_position_change=notify_server_position_change, account_service=account_service
)
price_monitor = PriceMonitor(position_service)
binance_service = BinanceService(price_monitor)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    log.info("🚀 Starting STM services...")
    # Start Binance WebSocket connection
    asyncio.create_task(binance_service.bookticker_loop())
    # Start price monitoring for SL/TP
    await price_monitor.start_monitoring()
    # Ensure account is initialized
    await account_service.ensure_account_initialized()
    log.info("🚀 STM services initialized")

    yield

    # Shutdown
    log.info("🛑 Shutting down STM services...")
    await price_monitor.stop_monitoring()


app = FastAPI(title="STM - Synth Trading Manager", version="0.1", lifespan=lifespan)

# Include routers
app.include_router(health.router)
app.include_router(account.router)
app.include_router(socket.router)
app.include_router(websocket.router)

# Inject position service into positions router
positions.set_position_service(position_service)
app.include_router(positions.router)

# Add middlewares
app.middleware("http")(log_requests_middleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
