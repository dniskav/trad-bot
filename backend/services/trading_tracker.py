#!/usr/bin/env python3
"""
Sistema de tracking de posiciones para el trading bot - Versión con múltiples posiciones por bot
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, Optional, Any
import logging
from utils.colored_logger import get_colored_logger
from persistence.file_repository import FilePersistenceRepository
from persistence.service import PersistenceService

# Usar logger con colores
logger = get_colored_logger(__name__)

# Archivos para persistencia (nuevo formato separado)
HISTORY_FILE = "logs/trading_history.json"  # legado (único)
BACKUP_FILE = "logs/trading_history_backup.json"

# Nuevo formato (separado por dominios)
HISTORY_FILE_NEW = "logs/history.json"
ACTIVE_POS_FILE_NEW = "logs/active_positions.json"
ACCOUNT_FILE_NEW = "logs/account.json"
BOT_STATUS_FILE_NEW = "logs/bot_status.json"


class TradingTracker:
    """Rastrea las posiciones de trading en tiempo real - Soporta múltiples posiciones por bot"""

    def __init__(self, binance_client=None):
        # Cliente de Binance para obtener balances en tiempo real
        self.binance_client = binance_client

        # Múltiples posiciones por bot (compatible con RealTradingManager)
        self.positions = {
            "conservative": {},  # Diccionario de posiciones múltiples
            "aggressive": {},  # Diccionario de posiciones múltiples
        }
        self.last_signals = {"conservative": "HOLD", "aggressive": "HOLD"}
        # Historial de posiciones cerradas
        self.position_history = []

        # Calcular balance inicial desde Binance
        self.initial_balance = self._calculate_initial_balance_from_binance(
            binance_client
        )
        self.current_balance = self.initial_balance
        self.total_pnl = 0.0

        # Inicializar servicio de persistencia (adaptador archivos por defecto)
        self.persistence = PersistenceService(
            FilePersistenceRepository(base_dir="logs")
        )

        # Cargar datos existentes al inicio (pero preservar el balance calculado)
        self.load_history()

        # Si no hay historial, usar el balance calculado desde Binance
        if not self.position_history:
            logger.info(
                f"💰 Usando balance inicial desde Binance: ${self.initial_balance:.2f}"
            )
        else:
            logger.info(
                f"💰 Balance inicial desde historial: ${self.initial_balance:.2f}"
            )
        # Comisiones de Binance (usando BNB para descuento)
        self.fee_rate = 0.00075  # 0.075% por trade con BNB
        self.total_fee_rate = 0.0015  # 0.15% total (compra + venta)

        # Stop Loss y Take Profit basados en recomendaciones de expertos para DOGE
        # Comisión total: 0.15% (BUY + SELL), ganancia mínima: 0.5%
        # DOGE: Alta volatilidad, soportes en $0.217, $0.210, $0.200
        self.stop_loss_config = {
            "conservative": {
                "stop_loss": 0.040,
                "take_profit": 0.020,
            },  # SL 4.0%, TP 2.0% (conservador para DOGE)
            "aggressive": {
                "stop_loss": 0.035,
                "take_profit": 0.018,
            },  # SL 3.5%, TP 1.8% (moderado-agresivo)
            "demo": {"stop_loss": 0.037, "take_profit": 0.019},  # 3.7% SL, 1.9% TP
        }

        # Inicializar saldo synthetic por defecto (500 USDT + 500 USDT en DOGE) si está vacío
        try:
            acc_syn = self.persistence.get_account_synth() or {}
            needs_init = (
                float(acc_syn.get("usdt_balance", 0.0)) == 0.0
                and float(acc_syn.get("doge_balance", 0.0)) == 0.0
                and float(acc_syn.get("current_balance", 0.0)) == 0.0
            )
            if needs_init:
                doge_price = self._get_current_doge_price() or 0.24
                usdt_balance = 500.0
                doge_balance = round(500.0 / doge_price, 6)
                total_usdt = usdt_balance + doge_balance * doge_price
                self.persistence.set_account_synth(
                    {
                        "initial_balance": total_usdt,
                        "current_balance": total_usdt,
                        "total_pnl": 0.0,
                        "usdt_balance": usdt_balance,
                        "doge_balance": doge_balance,
                        "doge_price": doge_price,
                        "total_balance_usdt": total_usdt,
                    }
                )
                logger.info(
                    f"💼 Synthetic account inicializada: USDT={usdt_balance:.2f}, DOGE={doge_balance} @ {doge_price:.5f}"
                )
        except Exception as _e:
            pass

    def _get_balance_from_binance(self, binance_client, detailed_logging=False):
        """Función común para obtener balance desde Binance (inicial o actual)"""
        if not binance_client:
            if detailed_logging:
                logger.warning(
                    "⚠️ Cliente de Binance no disponible, usando balance por defecto: $10.00"
                )
            return 10.0

        try:
            # Verificar si estamos usando margin trading
            leverage = int(os.getenv("LEVERAGE", "1"))

            if detailed_logging:
                # logger.info(f"🔍 DEBUG: Leverage detectado: {leverage}")
                pass

            if leverage > 1:
                # Usar cuenta de margen
                margin_account = binance_client.get_margin_account()

                if detailed_logging:
                    # logger.info(f"🔍 DEBUG: Margin get_margin_account keys: {list(margin_account.keys())}")
                    # Solo mostrar assets con balance > 0
                    relevant_assets = [
                        asset
                        for asset in margin_account.get("userAssets", [])
                        if float(asset.get("free", 0)) > 0
                        or float(asset.get("locked", 0)) > 0
                    ]
                    # logger.info(f"🔍 DEBUG: UserAssets relevantes: {relevant_assets}")

                # Obtener balances de la cuenta de margen
                usdt_balance = 0.0
                doge_balance = 0.0

                # Buscar balances en la cuenta de margen
                for asset in margin_account.get("userAssets", []):
                    if asset["asset"] == "USDT":
                        usdt_balance = float(asset["free"]) + float(asset["locked"])
                        # logger.info(f"🔍 DEBUG: USDT encontrado - free: {asset['free']}, locked: {asset['locked']}")
                    elif asset["asset"] == "DOGE":
                        doge_balance = float(asset["free"]) + float(asset["locked"])
                        # logger.info(f"🔍 DEBUG: DOGE encontrado - free: {asset['free']}, locked: {asset['locked']}")

                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol="DOGEUSDT")
                doge_price = float(ticker["price"])

                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)

                # Solo loggear si el balance cambió significativamente
                if (
                    not hasattr(self, "_last_balance")
                    or abs(total_balance - self._last_balance) > 0.01
                ):
                    # logger.info(f"🔍 DEBUG: Balance calculado - USDT: ${usdt_balance:.2f}, DOGE: {doge_balance:.2f}, Total: ${total_balance:.2f}")
                    self._last_balance = total_balance

                if detailed_logging:
                    logger.info(f"💰 Balance calculado desde Binance (Margin):")
                    logger.info(f"   USDT: ${usdt_balance:.2f}")
                    logger.info(
                        f"   DOGE: {doge_balance:.2f} (${doge_balance * doge_price:.2f})"
                    )
                    logger.info(f"   Total: ${total_balance:.2f}")
                    logger.info(
                        f"   Margin Level: {margin_account.get('marginLevel', 'N/A')}"
                    )

            else:
                # Usar cuenta spot normal
                account_info = binance_client.get_account()
                balances = {
                    balance["asset"]: float(balance["free"])
                    for balance in account_info["balances"]
                }

                usdt_balance = balances.get("USDT", 0.0)
                doge_balance = balances.get("DOGE", 0.0)

                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol="DOGEUSDT")
                doge_price = float(ticker["price"])

                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)

                if detailed_logging:
                    logger.info(f"💰 Balance calculado desde Binance (Spot):")
                    logger.info(f"   USDT: ${usdt_balance:.2f}")
                    logger.info(
                        f"   DOGE: {doge_balance:.2f} (${doge_balance * doge_price:.2f})"
                    )
                    logger.info(f"   Total: ${total_balance:.2f}")

            # logger.info(f"🔍 DEBUG: Función _get_balance_from_binance devolviendo: ${total_balance:.2f}")
            return total_balance

        except Exception as e:
            logger.error(f"❌ Error calculando balance desde Binance: {e}")
            return 10.0

    def _calculate_initial_balance_from_binance(self, binance_client):
        """Calcula el balance inicial desde Binance (USDT + DOGE convertido a USDT)"""
        return self._get_balance_from_binance(binance_client, detailed_logging=True)

    def _calculate_current_balance_from_binance(self, binance_client):
        """Calcula el balance actual desde Binance - usa la misma lógica que la función inicial"""
        # logger.info("🔍 DEBUG: Llamando _calculate_current_balance_from_binance()")

        if not binance_client:
            return self.current_balance

        try:
            # Verificar si estamos usando margin trading
            leverage = int(os.getenv("LEVERAGE", "1"))

            if leverage > 1:
                # Usar cuenta de margen
                margin_account = binance_client.get_margin_account()

                # Obtener balances de la cuenta de margen
                usdt_balance = 0.0
                doge_balance = 0.0

                # Buscar balances en la cuenta de margen
                for asset in margin_account.get("userAssets", []):
                    if asset["asset"] == "USDT":
                        usdt_balance = float(asset["free"]) + float(asset["locked"])
                    elif asset["asset"] == "DOGE":
                        doge_balance = float(asset["free"]) + float(asset["locked"])

                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol="DOGEUSDT")
                doge_price = float(ticker["price"])

                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)

            else:
                # Usar cuenta spot normal
                account_info = binance_client.get_account()
                balances = {
                    balance["asset"]: float(balance["free"])
                    for balance in account_info["balances"]
                }

                usdt_balance = balances.get("USDT", 0.0)
                doge_balance = balances.get("DOGE", 0.0)

                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol="DOGEUSDT")
                doge_price = float(ticker["price"])

                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)

            # logger.info(f"🔍 DEBUG: _calculate_current_balance_from_binance() devolviendo: ${total_balance:.2f}")
            return total_balance

        except Exception as e:
            logger.error(f"❌ Error calculando balance actual desde Binance: {e}")
            return self.current_balance

    def update_current_balance_from_binance(self):
        """Actualiza el balance actual desde Binance y calcula el PnL"""
        if not self.binance_client:
            return

        try:
            # Calcular balance actual desde Binance
            new_balance = self._calculate_current_balance_from_binance(
                self.binance_client
            )

            # logger.info(f"🔍 DEBUG: Balance calculado desde Binance: ${new_balance:.2f}")
            # logger.info(f"🔍 DEBUG: Balance anterior: ${self.current_balance:.2f}")

            # Actualizar balance actual
            self.current_balance = new_balance

            # Calcular PnL total basado en la diferencia con el balance inicial
            self.total_pnl = self.current_balance - self.initial_balance

            # Solo loggear si el balance cambió significativamente
            if (
                not hasattr(self, "_last_balance_binance")
                or abs(self.current_balance - self._last_balance_binance) > 0.01
            ):
                logger.info(
                    f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.4f})"
                )
                self._last_balance_binance = self.current_balance

        except Exception as e:
            logger.error(f"❌ Error actualizando balance desde Binance: {e}")

    def load_history(self):
        """Carga el historial de posiciones desde archivo"""
        try:
            # 1) Intentar cargar mediante el servicio de persistencia
            self.position_history = self.persistence.get_history()
            self.active_positions = self.persistence.get_active_positions() or {
                "conservative": {},
                "aggressive": {},
            }
            # Synthetic tracker debe leer su propia cuenta
            try:
                account_data = self.persistence.get_account_synth()
            except Exception:
                account_data = {
                    "initial_balance": self.initial_balance,
                    "current_balance": self.current_balance,
                    "total_pnl": self.total_pnl,
                }
            status = self.persistence.get_bot_status()

            self.bot_status = status or {"conservative": False, "aggressive": False}
            self.initial_balance = account_data.get(
                "initial_balance", self.initial_balance
            )
            self.current_balance = account_data.get(
                "current_balance", self.current_balance
            )
            self.total_pnl = account_data.get("total_pnl", self.total_pnl)

            logger.info(
                f"📂 (Nuevo formato) Historial cargado: {len(self.position_history)} posiciones"
            )
            logger.info(f"🤖 (Nuevo formato) Estado bots: {self.bot_status}")
            logger.info(
                f"📊 (Nuevo formato) Posiciones activas: { {k: len(v) for k,v in self.active_positions.items()} }"
            )

            # Agregar bots plug-and-play faltantes
            from .bot_registry import get_bot_registry

            bot_registry = get_bot_registry()
            for bot_name in bot_registry.get_all_bots().keys():
                if bot_name not in self.active_positions:
                    self.active_positions[bot_name] = {}

            # 2) Fallback: cargar del formato legado único si no hay historial cargado
            if not self.position_history and os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    self.position_history = data.get("history", [])

                    # Cargar estado de bots (por defecto inactivos)
                    self.bot_status = data.get(
                        "bot_status",
                        {
                            "conservative": False,  # Por defecto inactivo
                            "aggressive": False,  # Por defecto inactivo
                        },
                    )

                    # Cargar posiciones activas
                    default_active_positions = {"conservative": {}, "aggressive": {}}

                    # Agregar bots plug and play a las posiciones activas
                    from .bot_registry import get_bot_registry

                    bot_registry = get_bot_registry()
                    for bot_name in bot_registry.get_all_bots().keys():
                        if bot_name not in ["conservative", "aggressive"]:
                            default_active_positions[bot_name] = {}

                    # Cargar posiciones activas del archivo
                    loaded_active_positions = data.get(
                        "active_positions", default_active_positions
                    )

                    # Asegurar que todos los bots plug and play tengan su sección
                    for bot_name in bot_registry.get_all_bots().keys():
                        if bot_name not in loaded_active_positions:
                            loaded_active_positions[bot_name] = {}

                    # Forzar inclusión de bots plug and play
                    self.active_positions = loaded_active_positions
                    # Asegurar que siempre estén presentes los bots plug and play
                    for bot_name in bot_registry.get_all_bots().keys():
                        if bot_name not in self.active_positions:
                            self.active_positions[bot_name] = {}
                            logger.info(
                                f"✅ Bot plug and play agregado a active_positions: {bot_name}"
                            )

                    # HABILITADO PARA PRUEBA - Balance desde Binance
                    if self.binance_client:
                        logger.info(
                            "✅ Actualización de balance desde Binance HABILITADA PARA PRUEBA"
                        )
                        current_balance_from_binance = (
                            self._calculate_current_balance_from_binance(
                                self.binance_client
                            )
                        )
                        self.current_balance = current_balance_from_binance

                        # Calcular PnL total basado en la diferencia con el balance inicial
                        self.total_pnl = self.current_balance - self.initial_balance

                        logger.info(
                            f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f}"
                        )
                        logger.info(f"📊 PnL total calculado: ${self.total_pnl:.4f}")

                    # Solo usar datos guardados si no hay cliente de Binance
                    if not self.binance_client and not self.position_history:
                        self.initial_balance = data.get(
                            "initial_balance", self.initial_balance
                        )
                        self.current_balance = data.get(
                            "current_balance", self.current_balance
                        )
                        self.total_pnl = data.get("total_pnl", 0.0)

                logger.info(
                    f"📂 Historial cargado: {len(self.position_history)} posiciones"
                )
                logger.info(
                    f"🤖 Estado de bots cargado: Conservative={self.bot_status['conservative']}, Aggressive={self.bot_status['aggressive']}"
                )
                logger.info(
                    f"📊 Posiciones activas cargadas: Conservative={len(self.active_positions['conservative'])}, Aggressive={len(self.active_positions['aggressive'])}"
                )
            else:
                logger.info(
                    "📂 No se encontró archivo de historial, iniciando desde cero"
                )
                # Estado por defecto: ambos bots inactivos
                self.bot_status = {"conservative": False, "aggressive": False}
                # Posiciones activas por defecto
                self.active_positions = {"conservative": {}, "aggressive": {}}

                # Agregar bots plug and play a las posiciones activas
                from .bot_registry import get_bot_registry

                bot_registry = get_bot_registry()
                for bot_name in bot_registry.get_all_bots().keys():
                    if bot_name not in ["conservative", "aggressive"]:
                        self.active_positions[bot_name] = {}
        except Exception as e:
            logger.error(f"❌ Error cargando historial: {e}")
            self.position_history = []
            # Estado por defecto en caso de error
            self.bot_status = {"conservative": False, "aggressive": False}
            # Posiciones activas por defecto en caso de error
            self.active_positions = {"conservative": {}, "aggressive": {}}

            # Agregar bots plug and play a las posiciones activas
            from .bot_registry import get_bot_registry

            bot_registry = get_bot_registry()
            for bot_name in bot_registry.get_all_bots().keys():
                if bot_name not in ["conservative", "aggressive"]:
                    self.active_positions[bot_name] = {}

    def save_history(self):
        """Guarda el historial de posiciones en archivo"""
        try:
            # HABILITADO PARA PRUEBA - FUNCIÓN PRINCIPAL
            logger.info("✅ save_history() HABILITADO PARA PRUEBA")

            # Usar el servicio de persistencia
            self.persistence.set_history(self.position_history)
            self.persistence.set_active_positions(self.active_positions)
            # NO sobrescribir account_synth - ya fue persistido por adjust_synth_balances
            print(f"🔧 [DEBUG] Saltando sobrescritura de account_synth en save_history")
            logger.info(
                f"🔧 [DEBUG] Saltando sobrescritura de account_synth en save_history"
            )
            self.persistence.set_bot_status(self.bot_status)

            # Escritura legado deshabilitada

            # Log detallado del guardado del historial solo si cambió
            if len(self.position_history) > 0:
                last_trade = self.position_history[-1]

                # Solo loggear si el historial cambió
                if not hasattr(
                    self, "_last_history_count"
                ) or self._last_history_count != len(self.position_history):
                    logger.info(
                        f"💾 Historial guardado: {len(self.position_history)} posiciones"
                    )
                    self._last_history_count = len(self.position_history)

                # Solo loggear si el último trade cambió
                if not hasattr(
                    self, "_last_trade_id"
                ) or self._last_trade_id != last_trade.get("order_id"):
                    logger.info(
                        f"📈 Último trade: {last_trade['bot_type'].upper()} {last_trade['side']} - PnL: ${last_trade['net_pnl']:.4f}"
                    )
                    self._last_trade_id = last_trade.get("order_id")

                # Solo loggear si el balance cambió significativamente
                if (
                    not hasattr(self, "_last_balance_log")
                    or abs(self.current_balance - self._last_balance_log) > 0.01
                ):
                    logger.info(
                        f"💰 Balance actualizado: ${self.current_balance:.2f} (PnL total: ${self.total_pnl:.4f})"
                    )
                    self._last_balance_log = self.current_balance
            else:
                # Solo loggear si el historial cambió
                if not hasattr(
                    self, "_last_history_count"
                ) or self._last_history_count != len(self.position_history):
                    logger.info(
                        f"💾 Historial guardado: {len(self.position_history)} posiciones"
                    )
                    self._last_history_count = len(self.position_history)
        except Exception as e:
            logger.error(f"❌ Error guardando historial: {e}")

    def calculate_stop_loss_take_profit(
        self, bot_type: str, signal: str, entry_price: float
    ) -> tuple:
        """Calcula stop loss y take profit basado en el tipo de bot"""
        config = self.stop_loss_config.get(bot_type, self.stop_loss_config["demo"])

        if signal == "BUY":
            stop_loss = entry_price * (1 - config["stop_loss"])
            take_profit = entry_price * (1 + config["take_profit"])
        else:  # SELL
            stop_loss = entry_price * (1 + config["stop_loss"])
            take_profit = entry_price * (1 - config["take_profit"])

        return stop_loss, take_profit

    def get_bot_status(self) -> Dict[str, bool]:
        """Obtiene el estado actual de los bots"""
        return self.bot_status.copy()

    def update_bot_status(self, bot_type: str, is_active: bool):
        """Actualiza el estado de un bot y guarda el historial"""
        if bot_type in self.bot_status:
            self.bot_status[bot_type] = is_active
            # HABILITADO PARA PRUEBA
            logger.info("✅ save_history() HABILITADO PARA PRUEBA")
            self.save_history()  # Guardar inmediatamente el cambio de estado
            logger.info(
                f"🤖 Estado de bot {bot_type.upper()} actualizado: {'Activo' if is_active else 'Inactivo'}"
            )

    def update_position(
        self, bot_type: str, signal: str, current_price: float, quantity: float = 1.0
    ):
        """Actualiza las posiciones de un bot (soporta múltiples posiciones)"""
        # Asegurar estructura para bots PnP
        if bot_type not in self.positions:
            self.positions[bot_type] = {}
            try:
                if (
                    hasattr(self, "active_positions")
                    and bot_type not in self.active_positions
                ):
                    self.active_positions[bot_type] = {}
            except Exception:
                pass
        if bot_type not in self.last_signals:
            self.last_signals[bot_type] = "HOLD"
        # Si el bot cambió de señal de HOLD a BUY/SELL, abrir nueva posición
        if signal in ["BUY", "SELL"] and self.last_signals[bot_type] == "HOLD":

            # Calcular comisión de entrada
            entry_fee = current_price * quantity * self.fee_rate

            # Calcular stop loss y take profit
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(
                bot_type, signal, current_price
            )

            # Crear ID único para la posición
            position_id = f"{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

            # Abrir nueva posición
            self.positions[bot_type][position_id] = {
                "signal_type": signal,
                "entry_price": current_price,
                "quantity": quantity,
                "entry_time": datetime.now(),
                "current_price": current_price,
                "entry_fee": entry_fee,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "pnl_net": 0.0,
                "pnl_net_pct": 0.0,
            }

            logger.info(
                f"🚀 {bot_type.upper()} - Nueva posición {signal} a ${current_price:.4f} (ID: {position_id})"
            )

            # Ajustar balances synthetic si el bot es plug-and-play (no legacy)
            print(
                f"🔧 [DEBUG] Verificando condición: bot_type={bot_type}, no es legacy: {bot_type not in ['conservative', 'aggressive']}"
            )
            logger.info(
                f"🔧 [DEBUG] Verificando condición: bot_type={bot_type}, no es legacy: {bot_type not in ['conservative', 'aggressive']}"
            )
            if bot_type not in ["conservative", "aggressive"]:
                print(f"🔧 [DEBUG] Bloqueando saldo para apertura de {bot_type}")
                logger.info(f"🔧 [DEBUG] Bloqueando saldo para apertura de {bot_type}")

                # Paso 1: Bloquear saldo
                self.adjust_synth_balances(
                    side=signal,
                    action="open",
                    price=current_price,
                    quantity=quantity,
                    fee=entry_fee,
                )
            else:
                print(
                    f"🔧 [DEBUG] Saltando adjust_synth_balances para bot legacy: {bot_type}"
                )
                logger.info(
                    f"🔧 [DEBUG] Saltando adjust_synth_balances para bot legacy: {bot_type}"
                )

            # Registrar también en active_positions y persistir snapshot
            try:
                if not hasattr(self, "active_positions"):
                    self.active_positions = {"conservative": {}, "aggressive": {}}
                if bot_type not in self.active_positions:
                    self.active_positions[bot_type] = {}
                self.active_positions[bot_type][position_id] = {
                    "signal_type": signal,
                    "entry_price": current_price,
                    "quantity": quantity,
                    "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "current_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "status": "open",
                    "is_synthetic": bot_type not in ["conservative", "aggressive"],
                }
                # Persistir en archivo
                print(f"🔧 [DEBUG] Persistiendo posiciones activas para {bot_type}")
                logger.info(
                    f"🔧 [DEBUG] Persistiendo posiciones activas para {bot_type}"
                )
                self.persistence.set_active_positions(self.active_positions)
                print(f"🔧 [DEBUG] Posiciones activas persistidas exitosamente")
                logger.info(f"🔧 [DEBUG] Posiciones activas persistidas exitosamente")

                # Paso 2: Confirmar apertura exitosa y desbloquear saldo
                if bot_type not in ["conservative", "aggressive"]:
                    print(f"🔧 [DEBUG] Confirmando apertura exitosa para {bot_type}")
                    logger.info(
                        f"🔧 [DEBUG] Confirmando apertura exitosa para {bot_type}"
                    )
                    self.confirm_position_opening(
                        side=signal,
                        value=current_price * quantity,
                        quantity=quantity,
                        fee=entry_fee,
                    )
            except Exception as e:
                print(f"❌ [DEBUG] Error persistiendo posiciones activas: {e}")
                logger.error(f"❌ [DEBUG] Error persistiendo posiciones activas: {e}")
                pass

        # Si el bot cambió a HOLD, cerrar todas las posiciones abiertas
        elif signal == "HOLD" and self.last_signals[bot_type] in ["BUY", "SELL"]:

            # Cerrar todas las posiciones abiertas del bot
            positions_to_close = list(self.positions[bot_type].keys())

            for position_id in positions_to_close:
                position = self.positions[bot_type][position_id]
            position["exit_price"] = current_price
            position["exit_time"] = datetime.now()
            position["current_price"] = current_price

            # Calcular comisión de salida
            exit_fee = current_price * position["quantity"] * self.fee_rate
            position["exit_fee"] = exit_fee
            total_fees = position["entry_fee"] + exit_fee

            # Calcular PnL bruto
            if position["signal_type"] == "BUY":
                position["pnl"] = (current_price - position["entry_price"]) * position[
                    "quantity"
                ]
                position["pnl_pct"] = (
                    (current_price - position["entry_price"]) / position["entry_price"]
                ) * 100
            else:  # SELL
                position["pnl"] = (position["entry_price"] - current_price) * position[
                    "quantity"
                ]
                position["pnl_pct"] = (
                    (position["entry_price"] - current_price) / position["entry_price"]
                ) * 100

                # Calcular PnL neto
                position["pnl_net"] = position["pnl"] - total_fees
                position["pnl_net_pct"] = (
                    position["pnl_net"]
                    / (position["entry_price"] * position["quantity"])
                ) * 100
                position["total_fees"] = total_fees

                logger.info(
                    f"🔒 {bot_type.upper()} - Cerrando posición {position_id}: PnL ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)"
                )
                logger.info(
                    f"📊 Trade completado: {position['signal_type']} {position['quantity']} DOGE - Precio entrada: ${position['entry_price']:.6f} - Precio salida: ${position['exit_price']:.6f}"
                )
                logger.info(
                    f"💵 PnL Neto: ${position['pnl_net']:.4f} - Comisiones: ${total_fees:.4f}"
                )

                # Agregar al historial
                self.position_history.append(
                    {"bot_type": bot_type, "position_id": position_id, **position}
                )

                # Guardar historial inmediatamente cuando se cierra una posición
                # HABILITADO PARA PRUEBA
                logger.info("✅ save_history() HABILITADO PARA PRUEBA")
                self.save_history()

                # Actualizar saldo de cuenta
                self.update_balance(position["pnl_net"])

                # Ajustar balances synthetic en cierre si aplica
                if bot_type not in ["conservative", "aggressive"]:
                    self.adjust_synth_balances(
                        side=position["signal_type"],
                        action="close",
                        price=current_price,
                        quantity=position["quantity"],
                        fee=exit_fee,
                    )

                # Remover posición activa
                del self.positions[bot_type][position_id]

                # Remover de active_positions y persistir snapshot
                try:
                    if hasattr(self, "active_positions") and position_id in (
                        self.active_positions.get(bot_type, {}) or {}
                    ):
                        del self.active_positions[bot_type][position_id]
                        self.persistence.set_active_positions(self.active_positions)
                except Exception:
                    pass

        # Si tenemos posiciones abiertas, actualizar precios y PnL
        if self.positions[bot_type]:
            for position_id, position in self.positions[bot_type].items():
                position["current_price"] = current_price

                # Calcular PnL bruto actual
                if position["signal_type"] == "BUY":
                    position["pnl"] = (
                        current_price - position["entry_price"]
                    ) * position["quantity"]
                    position["pnl_pct"] = (
                        (current_price - position["entry_price"])
                        / position["entry_price"]
                    ) * 100
                else:  # SELL
                    position["pnl"] = (
                        position["entry_price"] - current_price
                    ) * position["quantity"]
                    position["pnl_pct"] = (
                        (position["entry_price"] - current_price)
                        / position["entry_price"]
                    ) * 100

                # Calcular PnL neto estimado (solo comisión de entrada por ahora)
                estimated_exit_fee = (
                    current_price * position["quantity"] * self.fee_rate
                )
                estimated_total_fees = position["entry_fee"] + estimated_exit_fee
                position["pnl_net"] = position["pnl"] - estimated_total_fees
                position["pnl_net_pct"] = (
                    position["pnl_net"]
                    / (position["entry_price"] * position["quantity"])
                ) * 100

        # Actualizar última señal
        self.last_signals[bot_type] = signal

    def update_balance(self, pnl_net: float):
        """Actualiza el balance de la cuenta"""
        self.total_pnl += pnl_net
        self.current_balance = self.initial_balance + self.total_pnl

        logger.info(
            f"💰 Saldo actualizado: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.2f})"
        )

    def get_account_balance(self) -> Dict[str, Any]:
        """Obtiene información del saldo de la cuenta"""
        # Proteger contra división por cero
        if self.initial_balance > 0:
            balance_change_pct = (
                (self.current_balance - self.initial_balance) / self.initial_balance
            ) * 100
        else:
            balance_change_pct = 0.0

        # Para synthetic: tomar balances desde persistencia (no desde Binance)
        usdt_balance = 0.0
        doge_balance = 0.0
        try:
            acc_syn = self.persistence.get_account_synth() or {}
            usdt_balance = float(acc_syn.get("usdt_balance", 0.0))
            doge_balance = float(acc_syn.get("doge_balance", 0.0))
        except Exception:
            pass

        # Obtener precio actual de DOGE
        doge_price = self._get_current_doge_price()

        total_balance_usdt = usdt_balance + (doge_balance * doge_price)
        # Leer datos existentes para obtener valores base
        try:
            acc_syn_full = self.persistence.get_account_synth() or {}
        except Exception:
            acc_syn_full = {}

        # Calcular valor actual de posiciones abiertas (con PnL)
        invested_amount = 0.0
        if hasattr(self, "active_positions"):
            for bot_type, positions in self.active_positions.items():
                if isinstance(positions, dict):
                    for pos_id, pos_data in positions.items():
                        if pos_data.get("status") == "open":
                            current_price = pos_data.get(
                                "current_price", pos_data.get("entry_price", 0)
                            )
                            quantity = pos_data.get("quantity", 0)
                            invested_amount += current_price * quantity

        # CALCULAR DINÁMICAMENTE LOS SALDOS BLOQUEADOS
        # Los saldos bloqueados solo deben existir si hay posiciones realmente abriéndose
        # Si todas las posiciones están confirmadas, los locked deben ser 0.0
        usdt_locked = float(acc_syn_full.get("usdt_locked", 0.0))
        doge_locked = float(acc_syn_full.get("doge_locked", 0.0))

        # Verificar si hay posiciones en proceso de apertura (no confirmadas)
        # Por ahora, mantener los valores del archivo
        # En el futuro, esto se puede expandir para detectar posiciones en proceso

        payload = {
            "initial_balance": float(
                acc_syn_full.get("initial_balance", self.initial_balance)
            ),
            "current_balance": total_balance_usdt,
            "total_pnl": float(acc_syn_full.get("total_pnl", self.total_pnl)),
            "balance_change_pct": balance_change_pct,
            "is_profitable": self.current_balance > self.initial_balance,
            "usdt_balance": usdt_balance,
            "doge_balance": doge_balance,
            "usdt_locked": usdt_locked,  # Calculado dinámicamente
            "doge_locked": doge_locked,  # Calculado dinámicamente
            "total_balance_usdt": total_balance_usdt,
            "doge_price": doge_price,
            "invested": invested_amount,  # Calcular dinámicamente
        }

        # Persistir con valores reales del archivo
        try:
            self.persistence.set_account_synth(
                {
                    "initial_balance": payload["initial_balance"],
                    "current_balance": payload["current_balance"],
                    "total_pnl": payload["total_pnl"],
                    "usdt_balance": usdt_balance,
                    "doge_balance": doge_balance,
                    "usdt_locked": usdt_locked,  # Usar valor real del archivo
                    "doge_locked": doge_locked,  # Usar valor real del archivo
                    "doge_price": doge_price,
                    "total_balance_usdt": total_balance_usdt,
                    "invested": invested_amount,  # Usar el valor calculado dinámicamente
                }
            )
        except Exception:
            pass

        return payload

    # --- Synthetic account helpers ---
    def _persist_synth_account(
        self, usdt_balance: float, doge_balance: float, doge_price: float
    ) -> None:
        total_usdt = usdt_balance + (doge_balance * doge_price)
        try:
            self.persistence.set_account_synth(
                {
                    "initial_balance": self.initial_balance,
                    "current_balance": total_usdt,
                    "total_pnl": self.total_pnl,
                    "usdt_balance": usdt_balance,
                    "doge_balance": doge_balance,
                    "doge_price": doge_price,
                    "total_balance_usdt": total_usdt,
                }
            )
        except Exception:
            pass

    def adjust_synth_balances(
        self, *, side: str, action: str, price: float, quantity: float, fee: float = 0.0
    ) -> None:
        """Adjust synthetic USDT/DOGE balances on open/close.

        action: 'open' or 'close'
        side: 'BUY' or 'SELL'
        """
        try:
            logger.info(
                f"🔧 [DEBUG] adjust_synth_balances llamado: side={side}, action={action}, price={price}, quantity={quantity}, fee={fee}"
            )

            acc = self.persistence.get_account_synth() or {}
            usdt = float(acc.get("usdt_balance", 0.0))
            doge = float(acc.get("doge_balance", 0.0))
            usdt_locked = float(acc.get("usdt_locked", 0.0))
            doge_locked = float(acc.get("doge_locked", 0.0))
            doge_price = self._get_current_doge_price()

            side = str(side).upper()
            action = str(action).lower()
            value = float(price) * float(quantity)

            try:
                logger.info(
                    f"[synth_balances][before] action={action} side={side} price={price:.6f} qty={quantity:.6f} fee={fee:.6f} | "
                    f"usdt={usdt:.6f} doge={doge:.6f} usdt_locked={usdt_locked:.6f} doge_locked={doge_locked:.6f}"
                )
            except Exception:
                pass

            if action == "open":
                if side == "BUY":
                    # Verificar saldo operativo (disponible - bloqueado)
                    usdt_operativo = usdt - usdt_locked
                    if usdt_operativo < value + fee:
                        return
                    # Bloquear USDT durante apertura
                    usdt_locked += value + fee
                    # NO modificar usdt_balance aún (se hará después si es exitoso)
                else:  # SELL
                    # Verificar saldo operativo (disponible - bloqueado)
                    doge_operativo = doge - doge_locked
                    if doge_operativo < quantity:
                        return
                    # Bloquear DOGE durante apertura
                    doge_locked += quantity
                    # NO modificar doge_balance aún (se hará después si es exitoso)
            else:  # close
                if side == "BUY":
                    # Cierre de BUY: el DOGE se convierte en USDT
                    # No necesitamos modificar balances aquí porque el dinero ya está "invertido"
                    # El PnL se calcula en close_order y se refleja en total_pnl
                    pass
                else:  # SELL
                    # Cierre de SELL: el USDT se convierte en DOGE
                    # No necesitamos modificar balances aquí porque el dinero ya está "invertido"
                    # El PnL se calcula en close_order y se refleja en total_pnl
                    pass

            # Clamp y persistencia con bloqueos
            usdt = max(0.0, usdt)
            doge = max(0.0, doge)
            total_usdt = usdt + doge * doge_price
            try:
                try:
                    logger.info(
                        f"[synth_balances][after] action={action} side={side} | "
                        f"usdt={usdt:.6f} doge={doge:.6f} usdt_locked={usdt_locked:.6f} doge_locked={doge_locked:.6f} total_usdt={total_usdt:.6f} doge_price={doge_price:.6f}"
                    )
                except Exception:
                    pass
                logger.info(
                    f"🔧 [DEBUG] Persistiendo saldo: usdt={usdt:.6f}, doge={doge:.6f}, total={total_usdt:.6f}"
                )
                # Calcular saldo disponible real
                initial_balance = float(acc.get("initial_balance", 1000.0))

                # El saldo disponible es el dinero que NO está invertido
                # Sumamos el dinero disponible (USDT + DOGE) menos el dinero bloqueado
                available_usdt = usdt - usdt_locked
                available_doge = doge - doge_locked
                available_balance = available_usdt + (available_doge * doge_price)

                # Calcular valor actual de posiciones abiertas (con PnL)
                invested_amount = 0.0
                if hasattr(self, "active_positions"):
                    for bot_type, positions in self.active_positions.items():
                        if isinstance(positions, dict):
                            for pos_id, pos_data in positions.items():
                                if pos_data.get("status") == "open":
                                    current_price = pos_data.get(
                                        "current_price", pos_data.get("entry_price", 0)
                                    )
                                    quantity = pos_data.get("quantity", 0)
                                    invested_amount += current_price * quantity

                # El saldo disponible real es el saldo inicial menos lo invertido
                available_balance = initial_balance - invested_amount

                account_data = {
                    "initial_balance": initial_balance,
                    "current_balance": available_balance,  # Solo saldo disponible
                    "total_pnl": float(acc.get("total_pnl", 0.0)),
                    "usdt_balance": usdt,
                    "doge_balance": doge,
                    "usdt_locked": usdt_locked,
                    "doge_locked": doge_locked,
                    "doge_price": doge_price,
                    "total_balance_usdt": available_balance,  # Solo saldo disponible
                    "invested": invested_amount,  # Valor actual de posiciones abiertas
                }

                print(f"🔧 [DEBUG] Datos a persistir: {account_data}")
                logger.info(f"🔧 [DEBUG] Datos a persistir: {account_data}")

                self.persistence.set_account_synth(account_data)

                print(f"🔧 [DEBUG] Saldo persistido exitosamente")
                logger.info(f"🔧 [DEBUG] Saldo persistido exitosamente")
            except Exception as e:
                logger.error(f"❌ [DEBUG] Error en persistencia: {e}")
        except Exception as e:
            logger.error(f"❌ [DEBUG] Error en adjust_synth_balances: {e}")

    def confirm_position_opening(
        self, side: str, value: float, quantity: float, fee: float = 0.0
    ) -> None:
        """
        Confirma que la apertura de posición fue exitosa y desbloquea el saldo.
        """
        try:
            logger.info(
                f"🔧 [DEBUG] confirm_position_opening: side={side}, value={value}, quantity={quantity}, fee={fee}"
            )

            acc = self.persistence.get_account_synth() or {}
            usdt = float(acc.get("usdt_balance", 0.0))
            doge = float(acc.get("doge_balance", 0.0))
            usdt_locked = float(acc.get("usdt_locked", 0.0))
            doge_locked = float(acc.get("doge_locked", 0.0))
            doge_price = self._get_current_doge_price()

            side = str(side).upper()

            if side == "BUY":
                # Confirmar apertura BUY: desbloquear USDT pero NO restar del balance disponible
                usdt_locked -= value + fee
                # NO hacer: usdt -= value + fee (el dinero se invierte, no se pierde)
                # El dinero se mueve de "disponible" a "invertido" automáticamente
            else:  # SELL
                # Confirmar apertura SELL: desbloquear DOGE pero NO restar del balance disponible
                doge_locked -= quantity
                # NO hacer: doge -= quantity (el dinero se invierte, no se pierde)
                # El dinero se mueve de "disponible" a "invertido" automáticamente

            # Persistir cambios
            usdt = max(0.0, usdt)
            doge = max(0.0, doge)
            usdt_locked = max(0.0, usdt_locked)
            doge_locked = max(0.0, doge_locked)

            available_balance = usdt + (doge * doge_price)

            # Calcular valor actual de posiciones abiertas (con PnL)
            invested_amount = 0.0
            if hasattr(self, "active_positions"):
                for bot_type, positions in self.active_positions.items():
                    if isinstance(positions, dict):
                        for pos_id, pos_data in positions.items():
                            if pos_data.get("status") == "open":
                                current_price = pos_data.get(
                                    "current_price", pos_data.get("entry_price", 0)
                                )
                                quantity = pos_data.get("quantity", 0)
                                invested_amount += current_price * quantity

            account_data = {
                "initial_balance": float(acc.get("initial_balance", 1000.0)),
                "current_balance": available_balance,  # Solo saldo disponible
                "total_pnl": float(acc.get("total_pnl", 0.0)),
                "usdt_balance": usdt,
                "doge_balance": doge,
                "usdt_locked": usdt_locked,
                "doge_locked": doge_locked,
                "doge_price": doge_price,
                "total_balance_usdt": available_balance,  # Solo saldo disponible
                "invested": invested_amount,  # Valor actual de posiciones abiertas
            }

            self.persistence.set_account_synth(account_data)
            logger.info(f"✅ [DEBUG] Apertura confirmada y saldo desbloqueado")

        except Exception as e:
            logger.error(f"❌ [DEBUG] Error confirmando apertura: {e}")

    def cancel_position_opening(
        self, side: str, value: float, quantity: float, fee: float = 0.0
    ) -> None:
        """
        Cancela la apertura de posición y desbloquea el saldo sin modificar balances.
        """
        try:
            logger.info(
                f"🔧 [DEBUG] cancel_position_opening: side={side}, value={value}, quantity={quantity}, fee={fee}"
            )

            acc = self.persistence.get_account_synth() or {}
            usdt_locked = float(acc.get("usdt_locked", 0.0))
            doge_locked = float(acc.get("doge_locked", 0.0))
            doge_price = self._get_current_doge_price()

            side = str(side).upper()

            if side == "BUY":
                # Cancelar BUY: solo desbloquear USDT
                usdt_locked -= value + fee
            else:  # SELL
                # Cancelar SELL: solo desbloquear DOGE
                doge_locked -= quantity

            # Persistir cambios (solo locked, no balances)
            usdt_locked = max(0.0, usdt_locked)
            doge_locked = max(0.0, doge_locked)

            account_data = {
                "initial_balance": float(acc.get("initial_balance", 1000.0)),
                "current_balance": float(acc.get("current_balance", 0.0)),
                "total_pnl": float(acc.get("total_pnl", 0.0)),
                "usdt_balance": float(acc.get("usdt_balance", 0.0)),
                "doge_balance": float(acc.get("doge_balance", 0.0)),
                "usdt_locked": usdt_locked,
                "doge_locked": doge_locked,
                "doge_price": doge_price,
                "total_balance_usdt": float(acc.get("total_balance_usdt", 0.0)),
            }

            self.persistence.set_account_synth(account_data)
            logger.info(f"✅ [DEBUG] Apertura cancelada y saldo desbloqueado")

        except Exception as e:
            logger.error(f"❌ [DEBUG] Error cancelando apertura: {e}")

    def _get_current_doge_price(self) -> float:
        """Obtiene el precio actual de DOGE en USDT"""
        if hasattr(self, "binance_client") and self.binance_client:
            try:
                ticker = self.binance_client.get_symbol_ticker(symbol="DOGEUSDT")
                return float(ticker["price"])
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener precio de DOGE: {e}")
        # Usar precio por defecto si no se puede obtener el precio real
        return 0.24215

    def get_position_info(self, bot_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de las posiciones actuales de un bot"""
        bot_positions = self.positions[bot_type]

        if not bot_positions:
            return None

        # Si solo hay una posición, devolverla directamente (compatibilidad con frontend)
        if len(bot_positions) == 1:
            return list(bot_positions.values())[0]

        # Si hay múltiples posiciones, devolver un resumen
        total_pnl = sum(pos["pnl"] for pos in bot_positions.values())
        total_pnl_net = sum(pos["pnl_net"] for pos in bot_positions.values())
        total_quantity = sum(pos["quantity"] for pos in bot_positions.values())

        # Usar la primera posición como base y agregar información de múltiples posiciones
        first_position = list(bot_positions.values())[0]

        return {
            **first_position,
            "multiple_positions": True,
            "position_count": len(bot_positions),
            "total_quantity": total_quantity,
            "total_pnl": total_pnl,
            "total_pnl_net": total_pnl_net,
            "all_positions": bot_positions,
        }

    def get_all_positions(self) -> Dict[str, Any]:
        """Obtiene información de todas las posiciones (compatible con frontend)"""
        return {
            "conservative": self.get_position_info("conservative"),
            "aggressive": self.get_position_info("aggressive"),
            "last_signals": self.last_signals,
            "history": self.get_position_history(limit=20),
            "statistics": {
                "conservative": self.get_bot_statistics("conservative"),
                "aggressive": self.get_bot_statistics("aggressive"),
                "overall": self.get_bot_statistics(),
            },
            "account_balance": self.get_account_balance(),
        }

    def get_position_history(self, limit: int = 50) -> list:
        """Obtiene el historial de posiciones cerradas"""
        return self.position_history[-limit:] if self.position_history else []

    def get_bot_statistics(self, bot_type: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas de un bot específico o generales"""
        if bot_type:
            # Estadísticas de un bot específico
            bot_history = [
                pos for pos in self.position_history if pos.get("bot_type") == bot_type
            ]

            if not bot_history:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "max_pnl": 0.0,
                    "min_pnl": 0.0,
                }

            winning_trades = [pos for pos in bot_history if pos.get("pnl_net", 0) > 0]
            losing_trades = [pos for pos in bot_history if pos.get("pnl_net", 0) < 0]

            total_pnl = sum(pos.get("pnl_net", 0) for pos in bot_history)

            return {
                "total_trades": len(bot_history),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": (
                    (len(winning_trades) / len(bot_history)) * 100 if bot_history else 0
                ),
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(bot_history) if bot_history else 0,
                "max_pnl": (
                    max(pos.get("pnl_net", 0) for pos in bot_history)
                    if bot_history
                    else 0
                ),
                "min_pnl": (
                    min(pos.get("pnl_net", 0) for pos in bot_history)
                    if bot_history
                    else 0
                ),
            }
        else:
            # Estadísticas generales
            if not self.position_history:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "max_pnl": 0.0,
                    "min_pnl": 0.0,
                }

            winning_trades = [
                pos for pos in self.position_history if pos.get("pnl_net", 0) > 0
            ]
            losing_trades = [
                pos for pos in self.position_history if pos.get("pnl_net", 0) < 0
            ]

            total_pnl = sum(pos.get("pnl_net", 0) for pos in self.position_history)

            return {
                "total_trades": len(self.position_history),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": (
                    (len(winning_trades) / len(self.position_history)) * 100
                    if self.position_history
                    else 0
                ),
                "total_pnl": total_pnl,
                "avg_pnl": (
                    total_pnl / len(self.position_history)
                    if self.position_history
                    else 0
                ),
                "max_pnl": (
                    max(pos.get("pnl_net", 0) for pos in self.position_history)
                    if self.position_history
                    else 0
                ),
                "min_pnl": (
                    min(pos.get("pnl_net", 0) for pos in self.position_history)
                    if self.position_history
                    else 0
                ),
            }

    def get_active_positions(self):
        """Retorna las posiciones activas"""
        return self.active_positions

    def update_active_position(
        self, bot_type: str, position_id: str, position_data: dict
    ):
        """Actualiza una posición activa"""
        if bot_type in self.active_positions:
            self.active_positions[bot_type][position_id] = position_data
            logger.info(
                f"📊 Posición activa actualizada: {bot_type.upper()} - {position_id}"
            )

    def remove_active_position(self, bot_type: str, position_id: str):
        """Remueve una posición activa"""
        if (
            bot_type in self.active_positions
            and position_id in self.active_positions[bot_type]
        ):
            del self.active_positions[bot_type][position_id]
            logger.info(
                f"📊 Posición activa removida: {bot_type.upper()} - {position_id}"
            )

    def clear_active_positions(self, bot_type: str = None):
        """Limpia las posiciones activas de un bot específico o de todos"""
        if bot_type:
            if bot_type in self.active_positions:
                self.active_positions[bot_type] = {}
                logger.info(f"📊 Posiciones activas limpiadas para {bot_type.upper()}")
        else:
            self.active_positions = {"conservative": {}, "aggressive": {}}

            # Agregar bots plug and play a las posiciones activas
            from .bot_registry import get_bot_registry

            bot_registry = get_bot_registry()
            for bot_name in bot_registry.get_all_bots().keys():
                if bot_name not in ["conservative", "aggressive"]:
                    self.active_positions[bot_name] = {}

            logger.info("📊 Todas las posiciones activas limpiadas")

    def _parse_datetime(self, dt_value):
        """Convierte un valor a datetime, manejando strings y objetos datetime"""
        if dt_value is None:
            return None

        if isinstance(dt_value, datetime):
            return dt_value

        if isinstance(dt_value, str):
            try:
                # Manejar diferentes formatos de fecha
                if "T" in dt_value:
                    return datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
                else:
                    # Formato simple sin timezone
                    return datetime.fromisoformat(dt_value)
            except ValueError:
                logger.warning(f"⚠️ No se pudo parsear fecha: {dt_value}")
                return datetime.now()

        return datetime.now()

    def create_order_record(
        self,
        bot_type: str,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        order_id: str,
        position_id: str,
    ) -> dict:
        """Crea y devuelve un registro de orden (YA NO se agrega al historial hasta que cierre)."""
        order_record = {
            "order_id": order_id,
            "position_id": position_id,
            "bot_type": bot_type,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "entry_time": datetime.now(),
            "status": "OPEN",  # OPEN, UPDATED, CLOSED
            "current_price": entry_price,
            "pnl": 0.0,
            "pnl_percentage": 0.0,
            "close_price": None,
            "close_time": None,
            "duration_minutes": 0,
            "fees_paid": 0.0,
            "net_pnl": 0.0,
        }
        # No agregar al historial aquí para mantener solo operaciones terminadas en disco
        logger.info(
            f"📝 Orden creada (no persistida en historial hasta cierre): {bot_type.upper()} {side} {quantity} {symbol} a ${entry_price}"
        )
        return order_record

    def update_order_status(
        self, order_id: str, current_price: float, status: str = "UPDATED"
    ):
        """Actualiza el estado de una orden en el historial"""
        for order in reversed(self.position_history):  # Buscar desde el más reciente
            if order["order_id"] == order_id:
                order["status"] = status
                order["current_price"] = current_price

                # Calcular PnL
                if order["side"] == "BUY":
                    order["pnl"] = (current_price - order["entry_price"]) * order[
                        "quantity"
                    ]
                    order["pnl_percentage"] = (
                        (current_price - order["entry_price"]) / order["entry_price"]
                    ) * 100
                else:  # SELL
                    order["pnl"] = (order["entry_price"] - current_price) * order[
                        "quantity"
                    ]
                    order["pnl_percentage"] = (
                        (order["entry_price"] - current_price) / order["entry_price"]
                    ) * 100

                # Calcular duración
                if order["entry_time"]:
                    entry_time = self._parse_datetime(order["entry_time"])
                    duration = datetime.now() - entry_time
                    order["duration_minutes"] = int(duration.total_seconds() / 60)

                logger.info(
                    f"📊 Orden actualizada: {order['bot_type'].upper()} PnL: ${order['pnl']:.4f} ({order['pnl_percentage']:.2f}%)"
                )
                return order

        logger.warning(f"⚠️ Orden {order_id} no encontrada en historial")
        return None

    def close_order(
        self,
        order_id: str,
        close_price: float,
        fees_paid: float = 0.0,
        reason: Optional[str] = None,
    ):
        """Cierra una orden en el historial con PnL final"""
        for order in reversed(self.position_history):
            if order["order_id"] == order_id:
                # Si ya existía (caso histórico), cerrar en sitio
                target = order
                break
        else:
            # Si no está en historial (nuevo flujo), intentar poblar desde active_positions
            bot_found = None
            pos_found = None
            try:
                for bname, positions in (self.active_positions or {}).items():
                    if not isinstance(positions, dict):
                        continue
                    if order_id in positions:
                        bot_found = bname
                        pos_found = positions[order_id]
                        break
                    for k, pos in positions.items():
                        pid = str(
                            pos.get("order_id")
                            or pos.get("id")
                            or pos.get("position_id")
                            or k
                        )
                        if pid == order_id:
                            bot_found = bname
                            pos_found = pos
                            break
                    if pos_found:
                        break
            except Exception:
                pos_found = None

            target = {
                "order_id": order_id,
                "position_id": order_id,
                "bot_type": str(bot_found or "unknown"),
                "symbol": "DOGEUSDT",
                "side": str(
                    (pos_found or {}).get("signal_type")
                    or (pos_found or {}).get("type")
                    or "BUY"
                ).upper(),
                "quantity": float(
                    (pos_found or {}).get("quantity")
                    or (pos_found or {}).get("qty")
                    or 0.0
                ),
                "entry_price": float(
                    (pos_found or {}).get("entry_price")
                    or (pos_found or {}).get("entry")
                    or 0.0
                ),
                "entry_time": (pos_found or {}).get("entry_time") or datetime.now(),
            }
            self.position_history.append(target)

        target["status"] = "CLOSED"
        target["close_price"] = close_price
        target["close_time"] = datetime.now()
        target["fees_paid"] = fees_paid
        if reason is not None:
            try:
                target["close_reason"] = str(reason)
            except Exception:
                target["close_reason"] = reason

        # Calcular PnL final de forma segura
        qty = float(target.get("quantity") or 0)
        entry = float(target.get("entry_price") or 0)
        side = str(target.get("side") or "BUY").upper()

        if side == "BUY":
            # Para BUY: Valor final del DOGE - USDT gastado (incluyendo fees)
            usdt_spent = entry * qty + fees_paid
            doge_value_final = close_price * qty
            target["pnl"] = doge_value_final - usdt_spent
            target["pnl_percentage"] = (
                ((close_price - entry) / entry) * 100 if entry else 0
            )
        else:  # SELL
            # Para SELL: USDT recibido - Valor del DOGE vendido (incluyendo fees)
            doge_value_sold = entry * qty
            usdt_received = close_price * qty - fees_paid
            target["pnl"] = usdt_received - doge_value_sold
            target["pnl_percentage"] = (
                ((entry - close_price) / entry) * 100 if entry else 0
            )

        target["net_pnl"] = target["pnl"]  # Ya incluye fees en el cálculo

        # Duración total
        if target.get("entry_time") and target.get("close_time"):
            entry_time = self._parse_datetime(target["entry_time"])
            close_time = self._parse_datetime(target["close_time"])
            duration = close_time - entry_time
            target["duration_minutes"] = int(duration.total_seconds() / 60)

        # Actualizar balance
        self.current_balance += target["net_pnl"]
        self.total_pnl += target["net_pnl"]

        logger.info("✅ save_history() HABILITADO PARA PRUEBA")
        self.save_history()

        logger.info(
            f"🔒 Orden cerrada: {target.get('bot_type','').upper()} {target.get('side','')} PnL: ${target.get('net_pnl',0):.4f} ({target.get('pnl_percentage',0):.2f}%)"
        )
        logger.info(
            f"💰 Balance actualizado: ${self.current_balance:.2f} (PnL total: ${self.total_pnl:.4f})"
        )

        return target

        logger.warning(f"⚠️ Orden {order_id} no encontrada en historial")
        return None

    def get_order_status(self, order_id: str) -> dict:
        """Obtiene el estado actual de una orden"""
        for order in reversed(self.position_history):
            if order["order_id"] == order_id:
                return order
        return None

    def get_open_orders(self) -> list:
        """Obtiene todas las órdenes abiertas (OPEN y UPDATED)"""
        return [
            order
            for order in self.position_history
            if order["status"] in ["OPEN", "UPDATED"]
        ]

    def get_closed_orders(self) -> list:
        """Obtiene todas las órdenes cerradas"""
        return [order for order in self.position_history if order["status"] == "CLOSED"]

    def update_current_balance_from_binance(self):
        """Actualiza el balance actual desde Binance"""
        if not self.binance_client:
            return

        try:
            # Usar la función común para obtener balance
            new_balance = self._calculate_current_balance_from_binance(
                self.binance_client
            )

            # Actualizar balance actual
            self.current_balance = new_balance

            # Calcular PnL total basado en la diferencia con el balance inicial
            self.total_pnl = self.current_balance - self.initial_balance

            # Solo loggear si el balance cambió significativamente
            if (
                not hasattr(self, "_last_balance_binance")
                or abs(self.current_balance - self._last_balance_binance) > 0.01
            ):
                logger.info(
                    f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.4f})"
                )
                self._last_balance_binance = self.current_balance

            return {"total_balance": new_balance, "total_pnl": self.total_pnl}

        except Exception as e:
            logger.error(f"❌ Error actualizando balance desde Binance: {e}")
            return None


# Instancia global del tracker - se inicializará con el cliente de Binance
trading_tracker = None


def initialize_tracker(binance_client=None):
    """Inicializa el tracker global"""
    global trading_tracker
    trading_tracker = TradingTracker(binance_client)
    return trading_tracker


def get_tracker():
    """Obtiene la instancia global del tracker"""
    global trading_tracker
    if trading_tracker is None:
        trading_tracker = TradingTracker()
    return trading_tracker
