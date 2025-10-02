import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.logger import get_logger
from backend.shared.settings import env_str

# Import routers
from .routers import health, websocket, socket, account, positions, strategies
from .services.websocket_manager import WebSocketManager
from .services.binance_service import BinanceService
from .services.stm_service import STMService
from .services.strategy_service import StrategyService
from .middlewares.logging import log_requests_middleware

log = get_logger("server.v0.2")
SYMBOL = env_str("SERVER_SYMBOL", "dogeusdt").lower()

# Initialize services
ws_manager = WebSocketManager()
binance_service = BinanceService(ws_manager)
stm_service = STMService()
strategy_service = StrategyService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    log.info("🚀 Starting Server v0.2 services...")

    # Check STM health
    stm_healthy = await stm_service.check_health()
    log.info(f"STM /health: {'ok' if stm_healthy else 'down'}")

    # Initialize strategy service
    await strategy_service.initialize(binance_service)

    # Inject strategy service into router AFTER initialization
    from .routers.strategies import set_strategy_service
    set_strategy_service(strategy_service)

    # Start background tasks
    asyncio.create_task(stm_service.heartbeat_loop())
    asyncio.create_task(binance_service.bookticker_loop())
    asyncio.create_task(binance_service.kline_loop(interval="1m"))

    log.info("🚀 Server v0.2 services initialized")

    yield

    # Shutdown
    log.info("🛑 Shutting down Server v0.2 services...")
    await strategy_service.shutdown()


app = FastAPI(title="Server v0.2", version="0.1", lifespan=lifespan)

# Include routers
app.include_router(health.router)
app.include_router(websocket.router)
app.include_router(socket.router)
app.include_router(account.router)
app.include_router(positions.router)
app.include_router(strategies.router)

# Add middlewares (order matters - CORS first, then logging)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(log_requests_middleware)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8200)
