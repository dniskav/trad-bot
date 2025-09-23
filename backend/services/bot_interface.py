#!/usr/bin/env python3
"""
Interfaz base para bots de trading plug-and-play
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime


class SignalType(Enum):
    """Tipos de señales de trading"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class BotConfig:
    """Configuración base para un bot"""

    name: str
    description: str
    version: str
    author: str
    symbol: str = "DOGEUSDT"
    interval: str = "1m"
    enabled: bool = True
    risk_level: str = "medium"  # low, medium, high
    max_positions: int = 5
    position_size: float = 1.0
    synthetic_mode: bool = False  # Modo synthetic para testing
    custom_params: Dict[str, Any] = None


@dataclass
class MarketData:
    """Datos de mercado para análisis"""

    symbol: str
    interval: str
    closes: List[float]
    highs: List[float]
    lows: List[float]
    volumes: List[float]
    timestamps: List[int]
    current_price: float


@dataclass
class TradingSignal:
    """Señal de trading generada por un bot"""

    bot_name: str
    signal_type: SignalType
    confidence: float  # 0.0 - 1.0
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: str = ""
    is_synthetic: bool = False  # Flag para operaciones sintéticas
    metadata: Dict[str, Any] = None


class BaseBot(ABC):
    """
    Clase base abstracta para todos los bots de trading
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.logger = logging.getLogger(f"bot.{config.name}")
        self.is_active = False
        self.positions = []
        self.last_signal = None
        self.synthetic_positions = []  # Posiciones sintéticas activas
        self.synthetic_balance = 1000.0  # Balance inicial para modo synthetic
        self.start_time: Optional[datetime] = None  # Tiempo de inicio del bot

    @abstractmethod
    def analyze_market(self, market_data: MarketData) -> TradingSignal:
        """
        Analiza los datos de mercado y genera una señal de trading

        Args:
            market_data: Datos de mercado actuales

        Returns:
            TradingSignal: Señal generada por el bot
        """
        pass

    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """
        Retorna la lista de indicadores técnicos que necesita el bot

        Returns:
            List[str]: Lista de nombres de indicadores (ej: ['SMA', 'RSI', 'MACD'])
        """
        pass

    def validate_config(self) -> bool:
        """
        Valida la configuración del bot

        Returns:
            bool: True si la configuración es válida
        """
        required_fields = ["name", "description", "version", "author"]
        for field in required_fields:
            if not getattr(self.config, field):
                self.logger.error(f"Campo requerido faltante: {field}")
                return False
        return True

    def start(self):
        """Inicia el bot"""
        if not self.validate_config():
            raise ValueError(f"Configuración inválida para bot {self.config.name}")

        self.is_active = True
        self.start_time = datetime.now()

        # Log detallado del inicio del bot
        mode_text = "sintético" if self.config.synthetic_mode else "real"
        self.logger.info(
            f"🚀 Bot {self.config.name} starting, synthetic: {self.config.synthetic_mode}"
        )
        self.logger.info(f"📊 Bot {self.config.name} iniciado en modo {mode_text}")
        self.logger.info(
            f"💰 Balance inicial: ${self.synthetic_balance:.2f}"
            if self.config.synthetic_mode
            else "💰 Modo real activado"
        )

    def stop(self):
        """Detiene el bot"""
        self.is_active = False
        self.start_time = None
        self.logger.info(f"🛑 Bot {self.config.name} stopping")
        self.logger.info(f"🛑 Bot {self.config.name} detenido")

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna el estado actual del bot

        Returns:
            Dict[str, Any]: Estado del bot
        """
        # Calcular tiempo transcurrido
        uptime_seconds = None
        uptime_formatted = None
        if self.is_active and self.start_time:
            uptime_delta = datetime.now() - self.start_time
            uptime_seconds = int(uptime_delta.total_seconds())

            # Formatear tiempo transcurrido
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60

            if hours > 0:
                uptime_formatted = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                uptime_formatted = f"{minutes}m {seconds}s"
            else:
                uptime_formatted = f"{seconds}s"

        return {
            "name": self.config.name,
            "description": self.config.description,
            "version": self.config.version,
            "author": self.config.author,
            "is_active": self.is_active,
            "positions_count": len(self.positions),
            "last_signal": self.last_signal.__dict__ if self.last_signal else None,
            "synthetic_mode": self.config.synthetic_mode,
            "synthetic_balance": (
                self.synthetic_balance if self.config.synthetic_mode else None
            ),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": uptime_formatted,
            "config": {
                "symbol": self.config.symbol,
                "interval": self.config.interval,
                "risk_level": self.config.risk_level,
                "max_positions": self.config.max_positions,
                "position_size": self.config.position_size,
                "synthetic_mode": self.config.synthetic_mode,
            },
        }

    def update_position(self, position_data: Dict[str, Any]):
        """
        Actualiza la información de una posición

        Args:
            position_data: Datos de la posición
        """
        # Implementación básica - puede ser sobrescrita por bots específicos
        self.positions.append(position_data)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de rendimiento del bot

        Returns:
            Dict[str, Any]: Métricas de rendimiento
        """
        return {
            "total_trades": len(self.positions),
            "active_positions": len(
                [p for p in self.positions if p.get("status") == "open"]
            ),
            "synthetic_trades": len(self.synthetic_positions),
            "synthetic_balance": self.synthetic_balance,
            "win_rate": 0.0,  # Implementar lógica específica
            "total_pnl": 0.0,  # Implementar lógica específica
            "last_signal_time": (
                self.last_signal.metadata.get("timestamp") if self.last_signal else None
            ),
        }

    def open_synthetic_position(
        self, signal: TradingSignal, current_price: float
    ) -> Dict[str, Any]:
        """
        Abre una posición sintética basada en una señal

        Args:
            signal: Señal de trading
            current_price: Precio actual del mercado

        Returns:
            Dict[str, Any]: Datos de la posición sintética
        """
        if not self.config.synthetic_mode:
            return None

        # Log antes de abrir posición
        self.logger.info(
            f"📈 Bot {self.config.name} intentando abrir posición {signal.signal_type.value} a precio ${current_price:.4f}"
        )

        # Calcular tamaño de posición
        position_size = self.config.position_size
        if signal.signal_type == SignalType.BUY:
            quantity = (self.synthetic_balance * 0.1) / current_price  # 10% del balance
        else:
            quantity = (self.synthetic_balance * 0.1) / current_price  # 10% del balance

        position = {
            "id": f"synthetic_{len(self.synthetic_positions) + 1}",
            "bot_name": self.config.name,
            "signal_type": signal.signal_type.value,
            "entry_price": current_price,
            "quantity": quantity,
            "stop_loss": signal.stop_loss,
            "take_profit": signal.take_profit,
            "status": "open",
            "is_synthetic": True,
            "timestamp": signal.metadata.get("timestamp") if signal.metadata else None,
            "reasoning": signal.reasoning,
        }

        # Asignar SL/TP por defecto si la señal no los trae (por ejemplo ±0.5%)
        try:
            default_pct = getattr(self.config, "default_sl_tp_pct", 0.005)
            entry = float(position["entry_price"])
            stype = position["signal_type"]
            if position["stop_loss"] is None or position["take_profit"] is None:
                if stype == "BUY":
                    position["stop_loss"] = (
                        position["stop_loss"]
                        if position["stop_loss"] is not None
                        else round(entry * (1 - default_pct), 6)
                    )
                    position["take_profit"] = (
                        position["take_profit"]
                        if position["take_profit"] is not None
                        else round(entry * (1 + default_pct), 6)
                    )
                elif stype == "SELL":
                    position["stop_loss"] = (
                        position["stop_loss"]
                        if position["stop_loss"] is not None
                        else round(entry * (1 + default_pct), 6)
                    )
                    position["take_profit"] = (
                        position["take_profit"]
                        if position["take_profit"] is not None
                        else round(entry * (1 - default_pct), 6)
                    )
        except Exception:
            pass

        self.synthetic_positions.append(position)
        self.logger.info(
            f"📊 Posición sintética abierta: {signal.signal_type.value} a ${current_price:.5f}"
        )

        return position

    def check_synthetic_positions(self, current_price: float) -> List[Dict[str, Any]]:
        """
        Verifica si alguna posición sintética debe cerrarse por SL/TP

        Args:
            current_price: Precio actual del mercado

        Returns:
            List[Dict[str, Any]]: Lista de posiciones cerradas
        """
        closed_positions = []

        for position in self.synthetic_positions[:]:  # Copia para iterar
            if position["status"] != "open":
                continue

            should_close = False
            close_reason = ""
            close_price = current_price

            # Verificar stop loss y take profit
            if position["signal_type"] == "BUY":
                if position["stop_loss"] and current_price <= position["stop_loss"]:
                    should_close = True
                    close_reason = "Stop Loss"
                    close_price = position["stop_loss"]
                elif (
                    position["take_profit"] and current_price >= position["take_profit"]
                ):
                    should_close = True
                    close_reason = "Take Profit"
                    close_price = position["take_profit"]
            else:  # SELL
                if position["stop_loss"] and current_price >= position["stop_loss"]:
                    should_close = True
                    close_reason = "Stop Loss"
                    close_price = position["stop_loss"]
                elif (
                    position["take_profit"] and current_price <= position["take_profit"]
                ):
                    should_close = True
                    close_reason = "Take Profit"
                    close_price = position["take_profit"]

            if should_close:
                # Calcular PnL
                if position["signal_type"] == "BUY":
                    pnl = (close_price - position["entry_price"]) * position["quantity"]
                else:
                    pnl = (position["entry_price"] - close_price) * position["quantity"]

                # Actualizar balance sintético
                self.synthetic_balance += pnl

                # Marcar posición como cerrada
                position["status"] = "closed"
                position["close_price"] = close_price
                position["close_reason"] = close_reason
                position["pnl"] = pnl
                position["close_time"] = int(datetime.now().timestamp())

                closed_positions.append(position)
                self.logger.info(
                    f"🔒 Posición sintética cerrada: {close_reason} - PnL: ${pnl:.2f}"
                )
                # Remover de activas
                try:
                    self.synthetic_positions.remove(position)
                except ValueError:
                    pass

        return closed_positions
