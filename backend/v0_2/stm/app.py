import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from backend.shared.logger import get_logger
from backend.shared.settings import env_str

# Import routers
from .routers import health, account, socket, websocket
from .services.account_service import AccountService
from .services.binance_service import BinanceService
from .middlewares.logging import log_requests_middleware

log = get_logger("stm.v0.2")

# Initialize services
account_service = AccountService()
binance_service = BinanceService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    log.info("🚀 Starting STM services...")
    # Start Binance WebSocket connection
    asyncio.create_task(binance_service.bookticker_loop())
    # Ensure account is initialized
    await account_service.ensure_account_initialized()
    log.info("🚀 STM services initialized")

    yield

    # Shutdown
    log.info("🛑 Shutting down STM services...")


app = FastAPI(title="STM - Synth Trading Manager", version="0.1", lifespan=lifespan)

# Include routers
app.include_router(health.router)
app.include_router(account.router)
app.include_router(socket.router)
app.include_router(websocket.router)

# Add middlewares
app.middleware("http")(log_requests_middleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
