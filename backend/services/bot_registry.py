#!/usr/bin/env python3
"""
Registro dinámico de bots de trading
"""

import os
import json
import importlib
import inspect
from typing import Dict, List, Type, Optional, Any
from pathlib import Path
import logging
from .bot_interface import BaseBot, BotConfig, TradingSignal


class BotRegistry:
    """
    Registro central para gestionar bots de trading
    Implementa patrón singleton para mantener estado entre llamadas
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Solo inicializar una vez
        if self._initialized:
            return

        self.bots: Dict[str, BaseBot] = {}
        self.bot_classes: Dict[str, Type[BaseBot]] = {}
        self.logger = logging.getLogger(__name__)
        self.bots_directory = Path(__file__).parent.parent / "bots"

        # Inicializar servicio de persistencia
        from persistence.file_repository import FilePersistenceRepository
        from persistence.service import PersistenceService

        self.persistence = PersistenceService(FilePersistenceRepository())

        # Crear directorio de bots si no existe
        self.bots_directory.mkdir(exist_ok=True)

        # Cargar bots existentes
        self._load_existing_bots()

        # Aplicar configuraciones guardadas
        self._apply_saved_configs()

        # Marcar como inicializado
        self._initialized = True

    def _load_existing_bots(self):
        """Carga bots existentes del sistema"""
        # Cargar bots hardcodeados existentes
        # self._load_legacy_bots()  # DESHABILITADO temporalmente

        # Cargar bots dinámicos del directorio bots/
        self._load_dynamic_bots()

    def _apply_saved_configs(self):
        """Aplica configuraciones guardadas a los bots existentes"""
        try:
            saved_configs = self.persistence.get_bot_configs()
            self.logger.info(
                f"📂 Cargando configuraciones guardadas: {list(saved_configs.keys())}"
            )

            for bot_name, config_data in saved_configs.items():
                bot = self.get_bot(bot_name)
                if bot:
                    # Aplicar configuración guardada
                    if "synthetic_mode" in config_data:
                        bot.config.synthetic_mode = config_data["synthetic_mode"]
                        self.logger.info(
                            f"🔄 Aplicando synthetic_mode={config_data['synthetic_mode']} a {bot_name}"
                        )

                    # Aplicar otros campos de configuración si existen
                    for key, value in config_data.items():
                        if hasattr(bot.config, key) and key != "synthetic_mode":
                            setattr(bot.config, key, value)
                            self.logger.info(f"🔄 Aplicando {key}={value} a {bot_name}")
                else:
                    self.logger.warning(
                        f"⚠️ Bot {bot_name} no encontrado para aplicar configuración guardada"
                    )

        except Exception as e:
            self.logger.error(f"❌ Error aplicando configuraciones guardadas: {e}")

    def _load_legacy_bots(self):
        """Carga bots legacy (conservative y aggressive)"""
        try:
            # Importar y registrar bot conservador
            from bots.sma_cross_bot import generate_signal as conservative_signal
            from bots.aggressive_scalping_bot import (
                generate_signal as aggressive_signal,
            )

            # Crear configuraciones para bots legacy
            conservative_config = BotConfig(
                name="conservative",
                description="Bot conservador SMA Cross (8/21) con filtros RSI y Volumen",
                version="1.0.0",
                author="Sistema Legacy",
                symbol="DOGEUSDT",
                interval="1m",
                risk_level="low",
                max_positions=5,
                position_size=1.0,
                synthetic_mode=False,
            )

            aggressive_config = BotConfig(
                name="aggressive",
                description="Bot agresivo SMA Cross (5/13) con filtros RSI y Volumen",
                version="1.0.0",
                author="Sistema Legacy",
                symbol="DOGEUSDT",
                interval="1m",
                risk_level="high",
                max_positions=5,
                position_size=1.5,
                synthetic_mode=False,
            )

            # Crear wrappers para bots legacy
            conservative_bot = LegacyBotWrapper(
                conservative_config, conservative_signal
            )
            aggressive_bot = LegacyBotWrapper(aggressive_config, aggressive_signal)

            self.register_bot(conservative_bot)
            self.register_bot(aggressive_bot)

            self.logger.info("✅ Bots legacy cargados: conservative, aggressive")

        except ImportError as e:
            self.logger.warning(f"⚠️ Error cargando bots legacy: {e}")

    def _load_dynamic_bots(self):
        """Carga bots dinámicos del directorio bots/"""
        if not self.bots_directory.exists():
            return

        for bot_file in self.bots_directory.glob("*.py"):
            if bot_file.name.startswith("__"):
                continue

            # Excluir archivos que no son bots plug-and-play
            if bot_file.name in ["aggressive_scalping_bot.py", "sma_cross_bot.py"]:
                continue

            try:
                module_name = f"bots.{bot_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, bot_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Buscar clases que hereden de BaseBot
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseBot)
                        and obj != BaseBot
                        and hasattr(obj, "__init__")
                    ):

                        # Intentar instanciar el bot con configuración por defecto
                        try:
                            # Buscar función de creación del bot (ej: create_simple_bot)
                            # Intentar diferentes variaciones del nombre
                            possible_names = [
                                f"create_{name.lower()}",  # create_simplebot
                                f"create_{name.lower().replace('bot', '_bot')}",  # create_simple_bot
                                f"create_{name.lower().replace('bot', '')}_bot",  # create_simple_bot
                            ]

                            create_func = None
                            for func_name in possible_names:
                                if hasattr(module, func_name):
                                    create_func = getattr(module, func_name)
                                    self.logger.info(
                                        f"✅ Encontrada función de creación: {func_name}"
                                    )
                                    break

                            if create_func:
                                # Usar la función de creación del bot que tiene la configuración correcta
                                bot_instance = create_func(name.lower())
                                self.logger.info(
                                    f"✅ Bot dinámico cargado con configuración personalizada: {name}"
                                )
                            else:
                                # Fallback: crear con configuración por defecto
                                config = BotConfig(
                                    name=name.lower(),
                                    description=f"Bot {name} cargado dinámicamente",
                                    version="1.0.0",
                                    author="Usuario",
                                    symbol="DOGEUSDT",
                                    interval="1m",
                                    synthetic_mode=False,
                                )
                                bot_instance = obj(config)
                                self.logger.info(
                                    f"✅ Bot dinámico cargado con configuración por defecto: {name}"
                                )

                            self.register_bot(bot_instance)

                        except Exception as e:
                            self.logger.error(f"❌ Error instanciando bot {name}: {e}")

            except Exception as e:
                self.logger.error(f"❌ Error cargando archivo {bot_file}: {e}")

    def register_bot(self, bot: BaseBot):
        """
        Registra un bot en el sistema

        Args:
            bot: Instancia del bot a registrar
        """
        if not isinstance(bot, BaseBot):
            raise ValueError("El bot debe heredar de BaseBot")

        if not bot.validate_config():
            raise ValueError(f"Configuración inválida para bot {bot.config.name}")

        self.bots[bot.config.name] = bot
        self.logger.info(f"📝 Bot registrado: {bot.config.name}")

    def unregister_bot(self, bot_name: str):
        """
        Desregistra un bot del sistema

        Args:
            bot_name: Nombre del bot a desregistrar
        """
        if bot_name in self.bots:
            bot = self.bots[bot_name]
            if bot.is_active:
                bot.stop()
            del self.bots[bot_name]
            self.logger.info(f"🗑️ Bot desregistrado: {bot_name}")
        else:
            self.logger.warning(f"⚠️ Bot no encontrado: {bot_name}")

    def get_bot(self, bot_name: str) -> Optional[BaseBot]:
        """
        Obtiene un bot por nombre

        Args:
            bot_name: Nombre del bot

        Returns:
            BaseBot o None si no se encuentra
        """
        return self.bots.get(bot_name)

    def get_all_bots(self) -> Dict[str, BaseBot]:
        """
        Retorna todos los bots registrados

        Returns:
            Dict con todos los bots
        """
        return self.bots.copy()

    def get_active_bots(self) -> Dict[str, BaseBot]:
        """
        Retorna solo los bots activos

        Returns:
            Dict con bots activos
        """
        return {name: bot for name, bot in self.bots.items() if bot.is_active}

    def start_bot(self, bot_name: str) -> bool:
        """
        Inicia un bot

        Args:
            bot_name: Nombre del bot

        Returns:
            bool: True si se inició correctamente
        """
        bot = self.get_bot(bot_name)
        if not bot:
            self.logger.error(f"❌ Bot no encontrado: {bot_name}")
            return False

        try:
            # Log antes de iniciar
            mode_text = "sintético" if bot.config.synthetic_mode else "real"
            self.logger.info(f"🚀 Iniciando bot {bot_name} en modo {mode_text}")

            bot.start()

            # Guardar configuración actualizada
            self._save_bot_config(bot_name)

            # Log después de iniciar
            self.logger.info(
                f"✅ Bot {bot_name} iniciado exitosamente en modo {mode_text}"
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Error iniciando bot {bot_name}: {e}")
            return False

    def stop_bot(self, bot_name: str) -> bool:
        """
        Detiene un bot

        Args:
            bot_name: Nombre del bot

        Returns:
            bool: True si se detuvo correctamente
        """
        bot = self.get_bot(bot_name)
        if not bot:
            self.logger.error(f"❌ Bot no encontrado: {bot_name}")
            return False

        try:
            # Log antes de detener
            self.logger.info(f"🛑 Deteniendo bot {bot_name}")

            bot.stop()

            # Guardar configuración actualizada
            self._save_bot_config(bot_name)

            # Log después de detener
            self.logger.info(f"✅ Bot {bot_name} detenido exitosamente")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo bot {bot_name}: {e}")
            return False

    def get_bot_status(self) -> Dict[str, Any]:
        """
        Retorna el estado de todos los bots

        Returns:
            Dict con estado de todos los bots
        """
        status = {}
        for name, bot in self.bots.items():
            status[name] = bot.get_status()
        return status

    def analyze_all_bots(self, market_data, signal_handler=None) -> Dict[str, Any]:
        """
        Ejecuta análisis de todos los bots activos y maneja señales automáticamente

        Args:
            market_data: Datos de mercado
            signal_handler: Manejador automático de señales (opcional)

        Returns:
            Dict con señales de todos los bots y resultados de acciones
        """
        signals = {}
        actions = {}

        for name, bot in self.get_active_bots().items():
            try:
                signal = bot.analyze_market(market_data)

                # Convertir signal a dict y serializar SignalType
                signal_dict = signal.__dict__.copy()

                # Remover campos no serializables
                if "id" in signal_dict:
                    del signal_dict["id"]

                # Convertir SignalType enum a string
                if "signal_type" in signal_dict:
                    signal_dict["signal_type"] = signal_dict["signal_type"].value

                # Verificar que no haya otros campos no serializables
                for key, value in list(signal_dict.items()):
                    try:
                        json.dumps(value)
                    except (TypeError, ValueError):
                        self.logger.warning(f"⚠️ Campo no serializable removido: {key}")
                        del signal_dict[key]

                signals[name] = signal_dict
                bot.last_signal = signal

                # Manejar señal automáticamente si hay signal_handler
                if signal_handler and signal.signal_type.value != "HOLD":
                    try:
                        action_result = signal_handler.handle_signal(signal)
                        actions[name] = action_result

                        if action_result.get("status") == "success":
                            self.logger.info(
                                f"✅ Acción ejecutada para {name}: {action_result.get('action', 'unknown')}"
                            )
                        elif action_result.get("status") == "skipped":
                            self.logger.info(
                                f"⏭️ Acción omitida para {name}: {action_result.get('message', 'unknown')}"
                            )
                        else:
                            self.logger.warning(
                                f"⚠️ Error en acción para {name}: {action_result.get('message', 'unknown')}"
                            )

                    except Exception as e:
                        self.logger.error(f"❌ Error manejando señal de {name}: {e}")
                        actions[name] = {"status": "error", "message": str(e)}

            except Exception as e:
                self.logger.error(f"❌ Error analizando bot {name}: {e}")
                signals[name] = {"error": str(e)}

        # Combinar señales y acciones en resultado
        result = {"signals": signals, "actions": actions if signal_handler else {}}

        return result

    def _save_bot_config(self, bot_name: str):
        """Guarda la configuración de un bot específico"""
        try:
            bot = self.get_bot(bot_name)
            if bot:
                # Obtener configuraciones existentes
                saved_configs = self.persistence.get_bot_configs()

                # Actualizar configuración del bot específico
                saved_configs[bot_name] = {
                    "synthetic_mode": bot.config.synthetic_mode,
                    "enabled": bot.config.enabled,
                    "risk_level": bot.config.risk_level,
                    "max_positions": bot.config.max_positions,
                    "position_size": bot.config.position_size,
                    "symbol": bot.config.symbol,
                    "interval": bot.config.interval,
                }

                # Guardar configuraciones actualizadas
                self.persistence.set_bot_configs(saved_configs)
                self.logger.info(
                    f"💾 Configuración guardada para {bot_name}: synthetic_mode={bot.config.synthetic_mode}"
                )

        except Exception as e:
            self.logger.error(f"❌ Error guardando configuración de {bot_name}: {e}")

    def update_bot_config(self, bot_name: str, config_updates: Dict[str, Any]):
        """Actualiza la configuración de un bot y la guarda"""
        try:
            bot = self.get_bot(bot_name)
            if not bot:
                self.logger.error(f"❌ Bot no encontrado: {bot_name}")
                return False

            # Aplicar actualizaciones
            for key, value in config_updates.items():
                if hasattr(bot.config, key):
                    setattr(bot.config, key, value)
                    self.logger.info(f"🔄 Actualizando {key}={value} para {bot_name}")
                else:
                    self.logger.warning(
                        f"⚠️ Campo {key} no existe en configuración de {bot_name}"
                    )

            # Guardar configuración actualizada
            self._save_bot_config(bot_name)
            return True

        except Exception as e:
            self.logger.error(f"❌ Error actualizando configuración de {bot_name}: {e}")
            return False


class LegacyBotWrapper(BaseBot):
    """
    Wrapper para bots legacy que no implementan la nueva interfaz
    """

    def __init__(self, config: BotConfig, signal_function):
        super().__init__(config)
        self.signal_function = signal_function

    def analyze_market(self, market_data) -> TradingSignal:
        """Analiza mercado usando función legacy"""
        from bot_interface import TradingSignal, SignalType

        try:
            # Llamar función legacy
            signal_str = self.signal_function(market_data.closes)

            # Convertir a enum
            if signal_str == "BUY":
                signal_type = SignalType.BUY
            elif signal_str == "SELL":
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD

            return TradingSignal(
                bot_name=self.config.name,
                signal_type=signal_type,
                confidence=0.8,  # Valor por defecto
                entry_price=market_data.current_price,
                reasoning=f"Señal legacy: {signal_str}",
                metadata={"type": "legacy", "timestamp": market_data.timestamps[-1]},
            )

        except Exception as e:
            self.logger.error(f"Error en análisis legacy: {e}")
            return TradingSignal(
                bot_name=self.config.name,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                entry_price=market_data.current_price,
                reasoning=f"Error: {str(e)}",
                metadata={"type": "legacy", "error": True},
            )

    def get_required_indicators(self) -> List[str]:
        """Indicadores requeridos para bots legacy"""
        return ["SMA", "RSI", "Volume"]


# Función para obtener la instancia singleton del registro
def get_bot_registry() -> BotRegistry:
    """
    Obtiene la instancia singleton del BotRegistry
    """
    return BotRegistry()


# Instancia global del registro (para compatibilidad)
bot_registry = get_bot_registry()
