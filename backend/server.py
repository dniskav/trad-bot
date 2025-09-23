#!/usr/bin/env python3
"""
Main FastAPI server - simplified and organized
"""

import signal
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import json
import asyncio
import threading
import time

# Core services
from services.real_trading_manager import RealTradingManager
from services.trading_tracker import TradingTracker
from services.bot_registry import bot_registry
from services.bot_interface import TradingSignal, SignalType
from persistence.service import PersistenceService
from persistence.file_repository import FilePersistenceRepository

# API modules (use backend/api modules, not features)
from api import health, trading, positions, bots, orders, klines, metrics
from websocket import manager as ws_manager

# Disable FastAPI access logs for polling endpoints
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.setLevel(logging.WARNING)

# Application logger
logger = logging.getLogger("server")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Initialize FastAPI app
app = FastAPI(
    title="SMA Cross Trading Bot API",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes para desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
manager = ws_manager.ConnectionManager()

# Initialize services
real_trading_manager = RealTradingManager()
trading_tracker = TradingTracker(real_trading_manager.client)

# Set dependencies for API modules
if hasattr(health, "set_dependencies"):
    health.set_dependencies()
trading.set_dependencies(trading_tracker)
positions.set_dependencies(real_trading_manager, trading_tracker, bot_registry, manager)
bots.set_dependencies(real_trading_manager, trading_tracker)
orders.set_dependencies(trading_tracker)
# klines no necesita dependencias - usa Binance directamente
metrics.set_dependencies(real_trading_manager, trading_tracker)

# Set dependencies for services
from services.position_service import set_dependencies as set_position_service_deps

set_position_service_deps(real_trading_manager, trading_tracker, bot_registry)

# Register routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(trading.router, prefix="/api", tags=["trading"])
app.include_router(positions.router, prefix="/api", tags=["positions"])
app.include_router(bots.router, prefix="/api", tags=["bots"])
app.include_router(orders.router, prefix="/api", tags=["orders"])
app.include_router(klines.router, prefix="/api", tags=["klines"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

# Import and register margin router
from api import margin

app.include_router(margin.router, prefix="/api", tags=["margin"])


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info("WebSocket client connected")

    try:
        # Send initial data
        await send_initial_data(websocket)

        # Start background task for periodic updates
        asyncio.create_task(periodic_data_updates(websocket))

        # Listen for client messages
        while True:
            try:
                # Wait for client message with timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await handle_client_message(websocket, data)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await manager.send_personal_message(
                    json.dumps(
                        {"type": "heartbeat", "timestamp": datetime.now().isoformat()}
                    ),
                    websocket,
                )
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


async def send_initial_data(websocket: WebSocket):
    """Send initial data when client connects"""
    try:
        # Get current price
        current_price = None
        try:
            current_price = real_trading_manager.get_current_price("DOGEUSDT")
        except:
            pass

        # Get candles and technical indicators data
        candles_and_indicators = None
        try:
            from services.technical_indicators import calculate_technical_indicators

            candles_and_indicators = calculate_technical_indicators(
                "DOGEUSDT", "1m", 100
            )
        except Exception as e:
            logger.error(f"Error getting initial candles and indicators: {e}")

        # Get position info
        from services.position_service import get_position_info_for_frontend

        position_info = get_position_info_for_frontend(current_price)

        # Try to produce initial bot signals using real data if available
        initial_bot_signals = None
        try:
            if candles_and_indicators and candles_and_indicators.get("candles"):
                from services.bot_interface import MarketData

                candles = candles_and_indicators["candles"]
                closes = [c["close"] for c in candles]
                highs = [c["high"] for c in candles]
                lows = [c["low"] for c in candles]
                volumes = [c["volume"] for c in candles]
                timestamps = [c["time"] for c in candles]
                md = MarketData(
                    symbol="DOGEUSDT",
                    interval="1m",
                    current_price=closes[-1] if closes else (current_price or 0.0),
                    closes=closes,
                    highs=highs,
                    lows=lows,
                    volumes=volumes,
                    timestamps=timestamps,
                )
                initial_bot_signals = bot_registry.analyze_all_bots(md)
        except Exception:
            initial_bot_signals = None

        # Send initial data
        initial_data = {
            "type": "initial_data",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "current_price": current_price,
                "active_positions": position_info.get("active_positions", {}),
                "account_balance": position_info.get("account_balance", {}),
                "bot_status": position_info.get("bot_status", {}),
                # "history" removido: el historial se consume solo vía REST
                "candles": (
                    candles_and_indicators.get("candles", [])
                    if candles_and_indicators
                    else []
                ),
                "indicators": (
                    candles_and_indicators.get("indicators", {})
                    if candles_and_indicators
                    else {}
                ),
                "bot_signals": initial_bot_signals or {},
            },
        }

        await manager.send_personal_message(json.dumps(initial_data), websocket)
        logger.info("Initial data sent to WebSocket client")

    except Exception as e:
        logger.error(f"Error sending initial data: {e}")


async def periodic_data_updates(websocket: WebSocket):
    """Send periodic updates every 3 seconds (pricing + snapshots)"""
    while True:
        try:
            await asyncio.sleep(3)  # Update every 3 seconds

            # Check if connection is still alive
            if websocket not in manager.active_connections:
                break

            # Get current price (best-effort)
            current_price = None
            try:
                current_price = real_trading_manager.get_current_price("DOGEUSDT")
            except Exception:
                current_price = None

            # Get candles and technical indicators data (best-effort)
            candles_and_indicators = None
            try:
                from services.technical_indicators import calculate_technical_indicators

                candles_and_indicators = calculate_technical_indicators(
                    "DOGEUSDT", "1m", 100
                )
            except Exception as e:
                logger.warning(f"Error getting candles/indicators (continuing): {e}")

            # Execute bot trading loop with real indicators data
            try:
                from services.bot_interface import MarketData

                # Use real indicators data if available, otherwise fallback to simulated data
                if candles_and_indicators and candles_and_indicators.get("candles"):
                    candles = candles_and_indicators["candles"]
                    indicators = candles_and_indicators["indicators"]

                    # Extract real data
                    closes = [candle["close"] for candle in candles]
                    highs = [candle["high"] for candle in candles]
                    lows = [candle["low"] for candle in candles]
                    volumes = [candle["volume"] for candle in candles]
                    timestamps = [candle["time"] for candle in candles]

                    # Get current price from the latest candle
                    if closes:
                        current_price = closes[-1]

                    market_data = MarketData(
                        symbol="DOGEUSDT",
                        interval="1m",
                        current_price=current_price or 0.0,
                        closes=closes,
                        highs=highs,
                        lows=lows,
                        volumes=volumes,
                        timestamps=timestamps,
                    )

                    logger.info(
                        f"📊 Using real market data: {len(closes)} candles, current price: ${current_price:.5f}"
                    )
                else:
                    # Fallback to simulated data
                    market_data = MarketData(
                        symbol="DOGEUSDT",
                        interval="1m",
                        current_price=current_price or 0.0,
                        closes=[current_price or 0.0] * 10,
                        highs=[current_price or 0.0] * 10,
                        lows=[current_price or 0.0] * 10,
                        volumes=[1000] * 10,
                        timestamps=[int(datetime.now().timestamp())] * 10,
                    )
                    logger.info("📊 Using simulated market data (fallback)")

                # Reconciliar SL/TP para posiciones sintéticas usando active_positions del tracker
                try:
                    all_bots = bot_registry.get_all_bots()
                    # Cargar snapshot en disco para fallback
                    snapshot_active = {}
                    try:
                        if (
                            hasattr(trading_tracker, "persistence")
                            and trading_tracker.persistence
                        ):
                            snapshot_active = (
                                trading_tracker.persistence.get_active_positions() or {}
                            )
                    except Exception:
                        snapshot_active = {}

                    for bot_name, bot in all_bots.items():
                        # Solo aplica a synthetic (por ahora)
                        if not getattr(bot.config, "synthetic_mode", False):
                            continue
                        mem_active = (
                            trading_tracker.active_positions.get(bot_name, {}) or {}
                        )
                        fs_active = snapshot_active.get(bot_name, {}) or {}

                        # Si memoria está vacía pero en disco hay datos, refrescar memoria con snapshot
                        if not mem_active and fs_active:
                            try:
                                trading_tracker.active_positions[bot_name] = dict(
                                    fs_active
                                )
                                mem_active = trading_tracker.active_positions[bot_name]
                                logger.info(
                                    f"♻️ Refrescadas active_positions en memoria para {bot_name} desde snapshot ({len(mem_active)} posiciones)"
                                )
                            except Exception:
                                pass

                        # Unir claves de memoria y snapshot para cubrir ambos casos
                        all_keys = set(mem_active.keys()) | set(fs_active.keys())
                        for position_id in all_keys:
                            pos = (
                                mem_active.get(position_id)
                                or fs_active.get(position_id)
                                or {}
                            )
                            stype = str(
                                pos.get("signal_type") or pos.get("type") or ""
                            ).upper()
                            sl = pos.get("stop_loss")
                            tp = pos.get("take_profit")
                            reason = None
                            close_price = None
                            if stype == "BUY":
                                if sl and current_price <= sl:
                                    reason = "Stop Loss"
                                    close_price = sl
                                elif tp and current_price >= tp:
                                    reason = "Take Profit"
                                    close_price = tp
                            elif stype == "SELL":
                                if sl and current_price >= sl:
                                    reason = "Stop Loss"
                                    close_price = sl
                                elif tp and current_price <= tp:
                                    reason = "Take Profit"
                                    close_price = tp
                            if reason and close_price is not None:
                                try:
                                    order_id = str(
                                        pos.get("order_id")
                                        or pos.get("id")
                                        or pos.get("position_id")
                                        or position_id
                                    )
                                    trading_tracker.close_order(
                                        order_id=order_id,
                                        close_price=float(close_price),
                                        fees_paid=0.0,
                                    )
                                    # Marcar la posición como cerrada en active_positions (flag) en vez de eliminarla
                                    try:
                                        updated = dict(pos)
                                        updated.update(
                                            {
                                                "status": "closed",
                                                "is_closed": True,
                                                "close_reason": reason,
                                                "close_price": float(close_price),
                                                "close_time": int(
                                                    datetime.now().timestamp()
                                                ),
                                            }
                                        )
                                        trading_tracker.update_active_position(
                                            bot_name, position_id, updated
                                        )
                                    except Exception:
                                        # Si falla la actualización, remover como fallback
                                        trading_tracker.remove_active_position(
                                            bot_name, position_id
                                        )
                                    logger.info(
                                        f"🔒 Reconciliador SL/TP cerró {bot_name} {position_id} por {reason} a ${close_price}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"❌ Error cerrando (reconciliador) {bot_name} {position_id}: {e}"
                                    )
                except Exception as e:
                    logger.error(f"Error en reconciliación SL/TP: {e}")

                bot_signals = bot_registry.analyze_all_bots(market_data)

                # Procesar señales y ejecutar trades
                for bot_name, signal in bot_signals.items():
                    if signal and "signal_type" in signal:
                        signal_type = signal.get("signal_type", "HOLD")
                        confidence = signal.get("confidence", 0.0)

                        # Log del bot y status
                        logger.info(f"🤖 {bot_name}: {signal_type}")

                        # Log del precio
                        logger.info(f"💰 Precio: ${current_price or 0.0:.5f}")

                        # Log de la confianza
                        logger.info(f"📊 Confianza: {confidence:.1%}")

                        # Ejecutar trade si la señal no es HOLD
                        if signal_type != "HOLD":
                            try:
                                bot = bot_registry.get_bot(bot_name)
                                if bot and bot.is_active:
                                    # Crear objeto TradingSignal para el bot
                                    from services.bot_interface import (
                                        TradingSignal,
                                        SignalType,
                                    )

                                    signal_obj = TradingSignal(
                                        bot_name=bot_name,
                                        signal_type=SignalType(signal_type),
                                        confidence=confidence,
                                        entry_price=current_price or 0.0,
                                        stop_loss=signal.get("stop_loss"),
                                        take_profit=signal.get("take_profit"),
                                        reasoning=signal.get("reasoning", ""),
                                        metadata=signal.get("metadata", {}),
                                    )

                                    # Ejecutar trade según el modo del bot
                                    if bot.config.synthetic_mode:
                                        # Modo sintético: abrir posición sintética
                                        position = bot.open_synthetic_position(
                                            signal_obj, current_price or 0.0
                                        )
                                        if position:
                                            logger.info(
                                                f"📈 {bot_name}: Posición sintética abierta - {signal_type} a ${current_price:.5f}"
                                            )

                                            # Crear registro en el historial para la posición sintética
                                            try:
                                                trading_tracker.create_order_record(
                                                    bot_type=bot_name,
                                                    symbol="DOGEUSDT",
                                                    side=signal_type,
                                                    quantity=position["quantity"],
                                                    entry_price=position["entry_price"],
                                                    order_id=f"SYNTH_{position['id']}",
                                                    position_id=position["id"],
                                                )
                                                logger.info(
                                                    f"📝 {bot_name}: Registro creado en historial para posición sintética {position['id']}"
                                                )
                                            except Exception as e:
                                                logger.error(
                                                    f"❌ {bot_name}: Error creando registro en historial: {e}"
                                                )

                                        # Verificar si hay posiciones sintéticas que deben cerrarse por SL/TP
                                        closed_positions = (
                                            bot.check_synthetic_positions(
                                                current_price or 0.0
                                            )
                                        )
                                        for closed_pos in closed_positions:
                                            logger.info(
                                                f"🔒 {bot_name}: Posición cerrada por {closed_pos['close_reason']} - PnL: ${closed_pos['pnl']:.2f}"
                                            )

                                        # Sincronizar posiciones sintéticas con el TradingTracker
                                        if bot.synthetic_positions:
                                            # Obtener posiciones abiertas
                                            open_positions = [
                                                pos
                                                for pos in bot.synthetic_positions
                                                if pos["status"] == "open"
                                            ]
                                            if open_positions:
                                                # Sincronizar con el tracker
                                                if (
                                                    bot_name
                                                    not in trading_tracker.active_positions
                                                ):
                                                    trading_tracker.active_positions[
                                                        bot_name
                                                    ] = {}

                                                for pos in open_positions:
                                                    position_id = pos["id"]
                                                    trading_tracker.active_positions[
                                                        bot_name
                                                    ][position_id] = {
                                                        "signal_type": pos[
                                                            "signal_type"
                                                        ],
                                                        "entry_price": pos[
                                                            "entry_price"
                                                        ],
                                                        "quantity": pos["quantity"],
                                                        "entry_time": pos["timestamp"],
                                                        "current_price": current_price
                                                        or pos["entry_price"],
                                                        "stop_loss": pos["stop_loss"],
                                                        "take_profit": pos[
                                                            "take_profit"
                                                        ],
                                                        "is_synthetic": True,
                                                    }

                                                # Guardar en archivo
                                                trading_tracker.save_history()
                                                logger.info(
                                                    f"💾 {bot_name}: {len(open_positions)} posiciones sintéticas sincronizadas con tracker"
                                                )
                                    else:
                                        # Modo real: usar RealTradingManager
                                        from services.real_trading_manager import (
                                            real_trading_manager,
                                        )

                                        result = real_trading_manager.place_order(
                                            bot_type=bot_name,
                                            signal=signal_type,
                                            current_price=current_price or 0.0,
                                            trading_tracker=trading_tracker,
                                        )
                                        if result.get("success"):
                                            logger.info(
                                                f"🚀 {bot_name}: Orden real ejecutada - {signal_type} a ${current_price:.5f}"
                                            )
                                        else:
                                            logger.error(
                                                f"❌ {bot_name}: Error ejecutando orden real: {result.get('error', 'Error desconocido')}"
                                            )

                            except Exception as e:
                                logger.error(
                                    f"❌ Error ejecutando trade para {bot_name}: {e}"
                                )
            except Exception as e:
                logger.error(f"Error in bot trading loop: {e}")

            # Always update PnL snapshot for active positions using current price
            try:
                fee_rate = getattr(trading_tracker, "fee_rate", 0.001)
                snapshot_active = trading_tracker.active_positions or {}
                for bot_name, positions in snapshot_active.items():
                    if not isinstance(positions, dict):
                        continue
                    for pid, pos in positions.items():
                        try:
                            qty = float(pos.get("quantity") or 0)
                            entry = float(pos.get("entry_price") or 0)
                            side = str(
                                pos.get("signal_type") or pos.get("type") or "BUY"
                            ).upper()
                            cp = float(
                                current_price or pos.get("current_price") or entry
                            )
                            # estimated pnl net (includes exit fee only)
                            pnl = (
                                (cp - entry) * qty
                                if side == "BUY"
                                else (entry - cp) * qty
                            )
                            est_exit_fee = cp * qty * float(fee_rate)
                            pnl_net = pnl - est_exit_fee
                            pos["current_price"] = cp
                            pos["pnl"] = pnl
                            pos["pnl_net"] = pnl_net
                        except Exception:
                            continue
            except Exception as e:
                logger.warning(f"Failed to update active positions snapshot: {e}")

            # Get updated position info (best-effort)
            try:
                from services.position_service import get_position_info_for_frontend

                position_info = get_position_info_for_frontend(current_price)
                if not isinstance(position_info, dict):
                    position_info = {}
            except Exception as e:
                logger.warning(f"Error getting position info (continuing): {e}")
                position_info = {}

            # Send update
            update_data = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "current_price": current_price,
                    "active_positions": position_info.get("active_positions", {}),
                    "account_balance": position_info.get("account_balance", {}),
                    "bot_status": position_info.get("bot_status", {}),
                    # "history" removido: el historial se consume solo vía REST
                    "candles": (
                        candles_and_indicators.get("candles", [])
                        if candles_and_indicators
                        else []
                    ),
                    "indicators": (
                        candles_and_indicators.get("indicators", {})
                        if candles_and_indicators
                        else {}
                    ),
                },
            }

            try:
                # Ensure update_data is JSON serializable (avoid TradingSignal objects)
                await manager.send_personal_message(
                    json.dumps(update_data, default=str), websocket
                )
            except Exception as e:
                logger.warning(f"Failed to send WS update (continuing): {e}")

        except Exception as e:
            # Do not stop the loop on transient errors; log and continue
            logger.error(f"Error in periodic updates (continuing): {e}")
            continue


async def handle_client_message(websocket: WebSocket, message: str):
    """Handle messages from client"""
    try:
        data = json.loads(message)
        message_type = data.get("type")

        if message_type == "ping":
            # Respond to ping
            await manager.send_personal_message(
                json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                websocket,
            )

        elif message_type == "request_update":
            # Send immediate update
            await send_initial_data(websocket)

        else:
            logger.warning(f"Unknown message type: {message_type}")

    except json.JSONDecodeError:
        logger.error("Invalid JSON received from client")
    except Exception as e:
        logger.error(f"Error handling client message: {e}")


# Legacy endpoints (to be moved to api/ modules)
# These will be moved to their respective api/ modules

# WebSocket handlers for real-time data implemented above


async def background_trading_loop():
    """Background task to execute bot trading loop every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)  # Wait 5 seconds

            # Get current price
            current_price = None
            try:
                current_price = real_trading_manager.get_current_price("DOGEUSDT")
            except:
                pass

            # Get candles and technical indicators data for background loop
            candles_and_indicators = None
            try:
                from services.technical_indicators import calculate_technical_indicators

                candles_and_indicators = calculate_technical_indicators(
                    "DOGEUSDT", "1m", 100
                )
            except Exception as e:
                logger.error(
                    f"Error getting candles and indicators in background loop: {e}"
                )

            # Execute bot trading loop with real indicators data
            try:
                from services.bot_interface import MarketData

                # Use real indicators data if available, otherwise fallback to simulated data
                if candles_and_indicators and candles_and_indicators.get("candles"):
                    candles = candles_and_indicators["candles"]
                    indicators = candles_and_indicators["indicators"]

                    # Extract real data
                    closes = [candle["close"] for candle in candles]
                    highs = [candle["high"] for candle in candles]
                    lows = [candle["low"] for candle in candles]
                    volumes = [candle["volume"] for candle in candles]
                    timestamps = [candle["time"] for candle in candles]

                    # Get current price from the latest candle
                    if closes:
                        current_price = closes[-1]

                    market_data = MarketData(
                        symbol="DOGEUSDT",
                        interval="1m",
                        current_price=current_price or 0.0,
                        closes=closes,
                        highs=highs,
                        lows=lows,
                        volumes=volumes,
                        timestamps=timestamps,
                    )

                    logger.info(
                        f"📊 Background loop using real market data: {len(closes)} candles, current price: ${current_price:.5f}"
                    )
                else:
                    # Fallback to simulated data
                    market_data = MarketData(
                        symbol="DOGEUSDT",
                        interval="1m",
                        current_price=current_price or 0.0,
                        closes=[current_price or 0.0] * 10,
                        highs=[current_price or 0.0] * 10,
                        lows=[current_price or 0.0] * 10,
                        volumes=[1000] * 10,
                        timestamps=[int(datetime.now().timestamp())] * 10,
                    )
                    logger.info(
                        "📊 Background loop using simulated market data (fallback)"
                    )

                bot_signals = bot_registry.analyze_all_bots(market_data)
                # Procesar señales y ejecutar trades
                for bot_name, signal in bot_signals.items():
                    if signal and "signal_type" in signal:
                        signal_type = signal.get("signal_type", "HOLD")
                        confidence = signal.get("confidence", 0.0)

                        # Log del bot y status
                        logger.info(f"🤖 {bot_name}: {signal_type}")

                        # Log del precio
                        logger.info(f"💰 Precio: ${current_price or 0.0:.5f}")

                        # Log de la confianza
                        logger.info(f"📊 Confianza: {confidence:.1%}")

                        # Ejecutar trade si la señal no es HOLD
                        if signal_type != "HOLD":
                            try:
                                bot = bot_registry.get_bot(bot_name)
                                if bot and bot.is_active:
                                    # Crear objeto TradingSignal para el bot
                                    from services.bot_interface import (
                                        TradingSignal,
                                        SignalType,
                                    )

                                    signal_obj = TradingSignal(
                                        bot_name=bot_name,
                                        signal_type=SignalType(signal_type),
                                        confidence=confidence,
                                        entry_price=current_price or 0.0,
                                        stop_loss=signal.get("stop_loss"),
                                        take_profit=signal.get("take_profit"),
                                        reasoning=signal.get("reasoning", ""),
                                        metadata=signal.get("metadata", {}),
                                    )

                                    # Ejecutar trade según el modo del bot
                                    if bot.config.synthetic_mode:
                                        # Modo sintético: abrir posición sintética
                                        position = bot.open_synthetic_position(
                                            signal_obj, current_price or 0.0
                                        )
                                        if position:
                                            logger.info(
                                                f"📈 {bot_name}: Posición sintética abierta - {signal_type} a ${current_price:.5f}"
                                            )

                                            # Crear registro en el historial para la posición sintética
                                            try:
                                                trading_tracker.create_order_record(
                                                    bot_type=bot_name,
                                                    symbol="DOGEUSDT",
                                                    side=signal_type,
                                                    quantity=position["quantity"],
                                                    entry_price=position["entry_price"],
                                                    order_id=f"SYNTH_{position['id']}",
                                                    position_id=position["id"],
                                                )
                                                logger.info(
                                                    f"📝 {bot_name}: Registro creado en historial para posición sintética {position['id']}"
                                                )
                                            except Exception as e:
                                                logger.error(
                                                    f"❌ {bot_name}: Error creando registro en historial: {e}"
                                                )

                                        # Verificar si hay posiciones sintéticas que deben cerrarse por SL/TP
                                        closed_positions = (
                                            bot.check_synthetic_positions(
                                                current_price or 0.0
                                            )
                                        )
                                        for closed_pos in closed_positions:
                                            logger.info(
                                                f"🔒 {bot_name}: Posición cerrada por {closed_pos['close_reason']} - PnL: ${closed_pos['pnl']:.2f}"
                                            )

                                        # Sincronizar posiciones sintéticas con el TradingTracker
                                        if bot.synthetic_positions:
                                            # Obtener posiciones abiertas
                                            open_positions = [
                                                pos
                                                for pos in bot.synthetic_positions
                                                if pos["status"] == "open"
                                            ]
                                            if open_positions:
                                                # Sincronizar con el tracker
                                                if (
                                                    bot_name
                                                    not in trading_tracker.active_positions
                                                ):
                                                    trading_tracker.active_positions[
                                                        bot_name
                                                    ] = {}

                                                for pos in open_positions:
                                                    position_id = pos["id"]
                                                    trading_tracker.active_positions[
                                                        bot_name
                                                    ][position_id] = {
                                                        "signal_type": pos[
                                                            "signal_type"
                                                        ],
                                                        "entry_price": pos[
                                                            "entry_price"
                                                        ],
                                                        "quantity": pos["quantity"],
                                                        "entry_time": pos["timestamp"],
                                                        "current_price": current_price
                                                        or pos["entry_price"],
                                                        "stop_loss": pos["stop_loss"],
                                                        "take_profit": pos[
                                                            "take_profit"
                                                        ],
                                                        "is_synthetic": True,
                                                    }

                                                # Guardar en archivo
                                                trading_tracker.save_history()
                                                logger.info(
                                                    f"💾 {bot_name}: {len(open_positions)} posiciones sintéticas sincronizadas con tracker"
                                                )
                                    else:
                                        # Modo real: usar RealTradingManager
                                        from services.real_trading_manager import (
                                            real_trading_manager,
                                        )

                                        result = real_trading_manager.place_order(
                                            bot_type=bot_name,
                                            signal=signal_type,
                                            current_price=current_price or 0.0,
                                            trading_tracker=trading_tracker,
                                        )
                                        if result.get("success"):
                                            logger.info(
                                                f"🚀 {bot_name}: Orden real ejecutada - {signal_type} a ${current_price:.5f}"
                                            )
                                        else:
                                            logger.error(
                                                f"❌ {bot_name}: Error ejecutando orden real: {result.get('error', 'Error desconocido')}"
                                            )

                            except Exception as e:
                                logger.error(
                                    f"❌ Error ejecutando trade para {bot_name}: {e}"
                                )
            except Exception as e:
                logger.error(f"Error in background trading loop: {e}")

        except Exception as e:
            logger.error(f"Error in background trading loop: {e}")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    asyncio.create_task(background_trading_loop())
    logger.info("🚀 Background trading loop started")


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.info("Starting FastAPI server (simplified version)...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
