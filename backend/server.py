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
from services.signal_handler import SignalHandler
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
signal_handler = SignalHandler(trading_tracker, real_trading_manager)

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
                initial_bot_analysis = bot_registry.analyze_all_bots(md, signal_handler)
                initial_bot_signals = initial_bot_analysis.get("signals", {})
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
                "account_balance_real": position_info.get("account_balance_real", {}),
                "account_balance_synthetic": position_info.get(
                    "account_balance_synthetic", {}
                ),
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

                # 1) Actualizar y persistir estados de cuenta (cada ~3s)
                try:
                    doge_price = float(current_price or 0.0)
                    if doge_price:
                        # Real: leer balances directamente de Binance
                        try:
                            balances = real_trading_manager.get_account_balance() or {}
                            usdt_real = float(balances.get("USDT", 0.0))
                            doge_real = float(balances.get("DOGE", 0.0))
                            total_real_usdt = usdt_real + (doge_real * doge_price)
                            trading_tracker.persistence.set_account_real(
                                {
                                    "initial_balance": 0.0,
                                    "current_balance": total_real_usdt,
                                    "total_pnl": 0.0,
                                    "usdt_balance": usdt_real,
                                    "doge_balance": doge_real,
                                    "doge_price": doge_price,
                                    "total_balance_usdt": total_real_usdt,
                                }
                            )
                        except Exception:
                            pass

                        # Synthetic: actualizar solo precio y totales; preservar balances y locks
                        try:
                            acc_syn = (
                                trading_tracker.persistence.get_account_synth() or {}
                            )
                            usdt_syn = float(acc_syn.get("usdt_balance", 0.0))
                            doge_syn = float(acc_syn.get("doge_balance", 0.0))
                            usdt_locked = float(acc_syn.get("usdt_locked", 0.0))
                            doge_locked = float(acc_syn.get("doge_locked", 0.0))
                            total_syn_usdt = usdt_syn + (doge_syn * doge_price)
                            trading_tracker.persistence.set_account_synth(
                                {
                                    "initial_balance": float(
                                        acc_syn.get("initial_balance", 0.0)
                                    ),
                                    "current_balance": total_syn_usdt,
                                    "total_pnl": float(acc_syn.get("total_pnl", 0.0)),
                                    "usdt_balance": usdt_syn,
                                    "doge_balance": doge_syn,
                                    "usdt_locked": usdt_locked,
                                    "doge_locked": doge_locked,
                                    "doge_price": doge_price,
                                    "total_balance_usdt": total_syn_usdt,
                                }
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

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

                            # Verificar si la posición ya está cerrada
                            is_closed = (
                                pos.get("status") == "closed"
                                or pos.get("is_closed") == True
                                or pos.get("close_reason") is not None
                                or pos.get("close_price") is not None
                            )

                            if is_closed:
                                # Saltar posiciones ya cerradas
                                continue

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
                                    # Usar util unificada para cierre synthetic (ajusta balances, history y active_positions)
                                    from services.close_utils import (
                                        close_synth_position,
                                    )

                                    # Asegurar que la posición exista en memoria del tracker antes de cerrar
                                    try:
                                        if (
                                            bot_name
                                            not in trading_tracker.active_positions
                                        ):
                                            trading_tracker.active_positions[
                                                bot_name
                                            ] = {}
                                        trading_tracker.active_positions[bot_name][
                                            position_id
                                        ] = dict(pos)
                                    except Exception:
                                        pass

                                    result = close_synth_position(
                                        trading_tracker=trading_tracker,
                                        real_trading_manager=real_trading_manager,
                                        bot_registry=bot_registry,
                                        bot_type=bot_name,
                                        position_id=str(
                                            pos.get("order_id")
                                            or pos.get("id")
                                            or pos.get("position_id")
                                            or position_id
                                        ),
                                        current_price=float(close_price),
                                        reason=reason,
                                    )

                                    # Safeguard: ensure account snapshot and history reflect the automatic close
                                    try:
                                        trading_tracker.save_history()
                                    except Exception:
                                        pass

                                    try:
                                        acc_now = (
                                            trading_tracker.persistence.get_account_synth()
                                            or {}
                                        )
                                        side_now = str(
                                            pos.get("signal_type")
                                            or pos.get("type")
                                            or "BUY"
                                        ).upper()
                                        qty_now = float(
                                            pos.get("quantity") or pos.get("qty") or 0.0
                                        )
                                        fee_rate = float(
                                            getattr(trading_tracker, "fee_rate", 0.001)
                                        )
                                        exit_fee = (
                                            float(close_price) * qty_now * fee_rate
                                        )
                                        doge_locked_now = float(
                                            acc_now.get("doge_locked", 0.0)
                                        )
                                        usdt_locked_now = float(
                                            acc_now.get("usdt_locked", 0.0)
                                        )

                                        if qty_now > 0:
                                            if (
                                                side_now == "BUY"
                                                and doge_locked_now >= qty_now
                                            ):
                                                trading_tracker.adjust_synth_balances(
                                                    side=side_now,
                                                    action="close",
                                                    price=float(close_price),
                                                    quantity=qty_now,
                                                    fee=exit_fee,
                                                )
                                            elif side_now == "SELL":
                                                need = (
                                                    float(close_price) * qty_now
                                                    + exit_fee
                                                )
                                                if usdt_locked_now >= need:
                                                    trading_tracker.adjust_synth_balances(
                                                        side=side_now,
                                                        action="close",
                                                        price=float(close_price),
                                                        quantity=qty_now,
                                                        fee=exit_fee,
                                                    )
                                    except Exception:
                                        pass

                                    # Salvaguarda: asegurar side-effects en cuenta e historial tras cierre automático
                                    try:
                                        # Forzar persistencia de historial
                                        trading_tracker.save_history()
                                    except Exception:
                                        pass

                                    # Refrescar snapshot desde la memoria del tracker (ya actualizada por close_synth_position)
                                    updated = (
                                        trading_tracker.active_positions.get(
                                            bot_name, {}
                                        )
                                        or {}
                                    ).get(position_id, {})
                                    if updated:
                                        snapshot_active[bot_name][position_id] = updated
                                        closed_map[position_id] = {
                                            "reason": updated.get(
                                                "close_reason", reason
                                            ),
                                            "close_price": float(
                                                updated.get("close_price", close_price)
                                            ),
                                        }

                                    logger.info(
                                        f"🔒 Reconciliador SL/TP cerró {bot_name} {position_id} por {reason} a ${close_price}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"❌ Error cerrando (reconciliador) {bot_name} {position_id}: {e}"
                                    )
                except Exception as e:
                    logger.error(f"Error en reconciliación SL/TP: {e}")

                # DESHABILITADO: Recalcular locks synthetic a partir de posiciones abiertas y persistir snapshot de cuenta
                # Este código estaba sobrescribiendo los balances correctos calculados por adjust_synth_balances
                # y causando inconsistencias en current_balance, usdt_locked, doge_locked e invested
                #
                # try:
                #     fee_rate = float(getattr(trading_tracker, "fee_rate", 0.001))
                #     acc_syn = trading_tracker.persistence.get_account_synth() or {}
                #     usdt_balance_now = float(acc_syn.get("usdt_balance", 0.0))
                #     doge_balance_now = float(acc_syn.get("doge_balance", 0.0))
                #     doge_price_now = float(
                #         current_price or acc_syn.get("doge_price", 0.0) or 0.0
                #     )
                #
                #     total_doge_locked = 0.0
                #     total_usdt_locked = 0.0
                #     try:
                #         snapshot_now = trading_tracker.active_positions or {}
                #         for bname, positions in snapshot_now.items():
                #             if not isinstance(positions, dict):
                #                 continue
                #             for _pid, p in positions.items():
                #                 try:
                #                     if str(p.get("status") or "open").lower() != "open":
                #                         continue
                #                     side = str(
                #                         p.get("signal_type") or p.get("type") or "BUY"
                #                     ).upper()
                #                     qty = float(
                #                         p.get("quantity") or p.get("qty") or 0.0
                #                     )
                #                     entry = float(
                #                         p.get("entry_price")
                #                         or p.get("entry")
                #                         or doge_price_now
                #                     )
                #                     if qty <= 0:
                #                         continue
                #                     if side == "BUY":
                #                         total_doge_locked += qty
                #                     else:
                #                         # SELL: lock USDT aproximado (valor - fee de entrada)
                #                         val = entry * qty
                #                         total_usdt_locked += max(
                #                             0.0, val - (val * fee_rate)
                #                         )
                #                 except Exception:
                #                     continue
                #     except Exception:
                #         pass
                #
                #     total_usdt_now = usdt_balance_now + doge_balance_now * (
                #         doge_price_now or 0.0
                #     )
                #     trading_tracker.persistence.set_account_synth(
                #         {
                #             "initial_balance": float(
                #                 acc_syn.get("initial_balance", 0.0)
                #             ),
                #             "current_balance": total_usdt_now,
                #             "total_pnl": float(acc_syn.get("total_pnl", 0.0)),
                #             "usdt_balance": usdt_balance_now,
                #             "doge_balance": doge_balance_now,
                #             "usdt_locked": total_usdt_locked,
                #             "doge_locked": total_doge_locked,
                #             "doge_price": doge_price_now,
                #             "total_balance_usdt": total_usdt_now,
                #         }
                #     )
                # except Exception as e:
                #     logger.warning(f"Failed to recompute/persist synthetic locks: {e}")

                logger.info(
                    "🔧 [DEBUG] Código problemático de recálculo de balances DESHABILITADO"
                )

                bot_analysis = bot_registry.analyze_all_bots(
                    market_data, signal_handler
                )
                bot_signals = bot_analysis.get("signals", {})
                bot_actions = bot_analysis.get("actions", {})

                # Procesar señales y ejecutar trades (legacy code - DESHABILITADO, ahora manejado por SignalHandler)
                # DESHABILITADO: Procesamiento legacy de señales
                # El SignalHandler ya procesa las señales automáticamente
                logger.info("📊 Señales procesadas automáticamente por SignalHandler")

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

                # 2) Sincronizar cierres reales con Binance (cada ~3s)
                try:
                    real_trading_manager.sync_with_binance_orders(trading_tracker)
                    real_trading_manager.sync_history_with_binance_orders(
                        trading_tracker
                    )
                    real_trading_manager.update_all_orders_status(trading_tracker)
                except Exception as e:
                    logger.warning(
                        f"Failed to sync real orders with Binance (continuing): {e}"
                    )

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
                    "account_balance_real": position_info.get(
                        "account_balance_real", {}
                    ),
                    "account_balance_synthetic": position_info.get(
                        "account_balance_synthetic", {}
                    ),
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

                bot_analysis = bot_registry.analyze_all_bots(
                    market_data, signal_handler
                )
                bot_signals = bot_analysis.get("signals", {})
                bot_actions = bot_analysis.get("actions", {})

                # Procesar señales y ejecutar trades (legacy code - DESHABILITADO, ahora manejado por SignalHandler)
                # DESHABILITADO: Procesamiento legacy de señales
                # El SignalHandler ya procesa las señales automáticamente
                logger.info("📊 Señales procesadas automáticamente por SignalHandler")
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
