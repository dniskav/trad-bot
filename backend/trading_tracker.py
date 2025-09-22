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
from colored_logger import get_colored_logger

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
            'conservative': {},  # Diccionario de posiciones múltiples
            'aggressive': {}      # Diccionario de posiciones múltiples
        }
        self.last_signals = {
            'conservative': 'HOLD',
            'aggressive': 'HOLD'
        }
        # Historial de posiciones cerradas
        self.position_history = []
        
        # Calcular balance inicial desde Binance
        self.initial_balance = self._calculate_initial_balance_from_binance(binance_client)
        self.current_balance = self.initial_balance
        self.total_pnl = 0.0
        
        # Cargar datos existentes al inicio (pero preservar el balance calculado)
        self.load_history()
        
        # Si no hay historial, usar el balance calculado desde Binance
        if not self.position_history:
            logger.info(f"💰 Usando balance inicial desde Binance: ${self.initial_balance:.2f}")
        else:
            logger.info(f"💰 Balance inicial desde historial: ${self.initial_balance:.2f}")
        # Comisiones de Binance (usando BNB para descuento)
        self.fee_rate = 0.00075  # 0.075% por trade con BNB
        self.total_fee_rate = 0.0015  # 0.15% total (compra + venta)
        
        # Stop Loss y Take Profit basados en recomendaciones de expertos para DOGE
        # Comisión total: 0.15% (BUY + SELL), ganancia mínima: 0.5%
        # DOGE: Alta volatilidad, soportes en $0.217, $0.210, $0.200
        self.stop_loss_config = {
            'conservative': {'stop_loss': 0.040, 'take_profit': 0.020},  # SL 4.0%, TP 2.0% (conservador para DOGE)
            'aggressive': {'stop_loss': 0.035, 'take_profit': 0.018},   # SL 3.5%, TP 1.8% (moderado-agresivo)
            'demo': {'stop_loss': 0.037, 'take_profit': 0.019}           # 3.7% SL, 1.9% TP
        }
    
    def _get_balance_from_binance(self, binance_client, detailed_logging=False):
        """Función común para obtener balance desde Binance (inicial o actual)"""
        if not binance_client:
            if detailed_logging:
                logger.warning("⚠️ Cliente de Binance no disponible, usando balance por defecto: $10.00")
            return 10.0
        
        try:
            # Verificar si estamos usando margin trading
            leverage = int(os.getenv('LEVERAGE', '1'))
            
            if detailed_logging:
                # logger.info(f"🔍 DEBUG: Leverage detectado: {leverage}")
                pass
            
            if leverage > 1:
                # Usar cuenta de margen
                margin_account = binance_client.get_margin_account()
                
                if detailed_logging:
                    # logger.info(f"🔍 DEBUG: Margin account keys: {list(margin_account.keys())}")
                    # Solo mostrar assets con balance > 0
                    relevant_assets = [asset for asset in margin_account.get('userAssets', []) 
                                     if float(asset.get('free', 0)) > 0 or float(asset.get('locked', 0)) > 0]
                    # logger.info(f"🔍 DEBUG: UserAssets relevantes: {relevant_assets}")
                
                # Obtener balances de la cuenta de margen
                usdt_balance = 0.0
                doge_balance = 0.0
                
                # Buscar balances en la cuenta de margen
                for asset in margin_account.get('userAssets', []):
                    if asset['asset'] == 'USDT':
                        usdt_balance = float(asset['free']) + float(asset['locked'])
                        # logger.info(f"🔍 DEBUG: USDT encontrado - free: {asset['free']}, locked: {asset['locked']}")
                    elif asset['asset'] == 'DOGE':
                        doge_balance = float(asset['free']) + float(asset['locked'])
                        # logger.info(f"🔍 DEBUG: DOGE encontrado - free: {asset['free']}, locked: {asset['locked']}")
                
                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol='DOGEUSDT')
                doge_price = float(ticker['price'])
                
                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)
                
                # Solo loggear si el balance cambió significativamente
                if not hasattr(self, '_last_balance') or abs(total_balance - self._last_balance) > 0.01:
                    # logger.info(f"🔍 DEBUG: Balance calculado - USDT: ${usdt_balance:.2f}, DOGE: {doge_balance:.2f}, Total: ${total_balance:.2f}")
                    self._last_balance = total_balance
                
                if detailed_logging:
                    logger.info(f"💰 Balance calculado desde Binance (Margin):")
                    logger.info(f"   USDT: ${usdt_balance:.2f}")
                    logger.info(f"   DOGE: {doge_balance:.2f} (${doge_balance * doge_price:.2f})")
                    logger.info(f"   Total: ${total_balance:.2f}")
                    logger.info(f"   Margin Level: {margin_account.get('marginLevel', 'N/A')}")
                
            else:
                # Usar cuenta spot normal
                account_info = binance_client.get_account()
                balances = {balance['asset']: float(balance['free']) for balance in account_info['balances']}
                
                usdt_balance = balances.get('USDT', 0.0)
                doge_balance = balances.get('DOGE', 0.0)
                
                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol='DOGEUSDT')
                doge_price = float(ticker['price'])
                
                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)
                
                if detailed_logging:
                    logger.info(f"💰 Balance calculado desde Binance (Spot):")
                    logger.info(f"   USDT: ${usdt_balance:.2f}")
                    logger.info(f"   DOGE: {doge_balance:.2f} (${doge_balance * doge_price:.2f})")
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
            leverage = int(os.getenv('LEVERAGE', '1'))
            
            if leverage > 1:
                # Usar cuenta de margen
                margin_account = binance_client.get_margin_account()
                
                # Obtener balances de la cuenta de margen
                usdt_balance = 0.0
                doge_balance = 0.0
                
                # Buscar balances en la cuenta de margen
                for asset in margin_account.get('userAssets', []):
                    if asset['asset'] == 'USDT':
                        usdt_balance = float(asset['free']) + float(asset['locked'])
                    elif asset['asset'] == 'DOGE':
                        doge_balance = float(asset['free']) + float(asset['locked'])
                
                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol='DOGEUSDT')
                doge_price = float(ticker['price'])
                
                # Calcular balance total en USDT
                total_balance = usdt_balance + (doge_balance * doge_price)
                
            else:
                # Usar cuenta spot normal
                account_info = binance_client.get_account()
                balances = {balance['asset']: float(balance['free']) for balance in account_info['balances']}
                
                usdt_balance = balances.get('USDT', 0.0)
                doge_balance = balances.get('DOGE', 0.0)
                
                # Obtener precio actual de DOGE para convertir a USDT
                ticker = binance_client.get_symbol_ticker(symbol='DOGEUSDT')
                doge_price = float(ticker['price'])
                
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
            new_balance = self._calculate_current_balance_from_binance(self.binance_client)
            
            # logger.info(f"🔍 DEBUG: Balance calculado desde Binance: ${new_balance:.2f}")
            # logger.info(f"🔍 DEBUG: Balance anterior: ${self.current_balance:.2f}")
            
            # Actualizar balance actual
            self.current_balance = new_balance
            
            # Calcular PnL total basado en la diferencia con el balance inicial
            self.total_pnl = self.current_balance - self.initial_balance
            
            # Solo loggear si el balance cambió significativamente
            if not hasattr(self, '_last_balance_binance') or abs(self.current_balance - self._last_balance_binance) > 0.01:
                logger.info(f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.4f})")
                self._last_balance_binance = self.current_balance
            
        except Exception as e:
            logger.error(f"❌ Error actualizando balance desde Binance: {e}")
    
    def load_history(self):
        """Carga el historial de posiciones desde archivo"""
        try:
            # 1) Intentar cargar desde el nuevo formato (archivos separados)
            if all(os.path.exists(p) for p in [HISTORY_FILE_NEW, ACTIVE_POS_FILE_NEW, ACCOUNT_FILE_NEW, BOT_STATUS_FILE_NEW]):
                # Historial
                with open(HISTORY_FILE_NEW, 'r') as f:
                    self.position_history = json.load(f)

                # Estado de bots
                with open(BOT_STATUS_FILE_NEW, 'r') as f:
                    self.bot_status = json.load(f)

                # Posiciones activas
                with open(ACTIVE_POS_FILE_NEW, 'r') as f:
                    self.active_positions = json.load(f)

                # Cuenta
                with open(ACCOUNT_FILE_NEW, 'r') as f:
                    account = json.load(f)
                    self.initial_balance = account.get('initial_balance', self.initial_balance)
                    self.current_balance = account.get('current_balance', self.current_balance)
                    self.total_pnl = account.get('total_pnl', self.total_pnl)

                logger.info(f"📂 (Nuevo formato) Historial cargado: {len(self.position_history)} posiciones")
                logger.info(f"🤖 (Nuevo formato) Estado bots: {self.bot_status}")
                logger.info(f"📊 (Nuevo formato) Posiciones activas: { {k: len(v) for k,v in self.active_positions.items()} }")

                # Agregar bots plug-and-play faltantes
                from bot_registry import get_bot_registry
                bot_registry = get_bot_registry()
                for bot_name in bot_registry.get_all_bots().keys():
                    if bot_name not in self.active_positions:
                        self.active_positions[bot_name] = {}

            # 2) Fallback: cargar del formato legado único
            elif os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.position_history = data.get('history', [])
                    
                    # Cargar estado de bots (por defecto inactivos)
                    self.bot_status = data.get('bot_status', {
                        'conservative': False,  # Por defecto inactivo
                        'aggressive': False     # Por defecto inactivo
                    })
                    
                    # Cargar posiciones activas
                    default_active_positions = {
                        'conservative': {},
                        'aggressive': {}
                    }
                    
                    # Agregar bots plug and play a las posiciones activas
                    from bot_registry import get_bot_registry
                    bot_registry = get_bot_registry()
                    for bot_name in bot_registry.get_all_bots().keys():
                        if bot_name not in ['conservative', 'aggressive']:
                            default_active_positions[bot_name] = {}
                    
                    # Cargar posiciones activas del archivo
                    loaded_active_positions = data.get('active_positions', default_active_positions)
                    
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
                            logger.info(f"✅ Bot plug and play agregado a active_positions: {bot_name}")
                    
                    # HABILITADO PARA PRUEBA - Balance desde Binance
                    if self.binance_client:
                        logger.info("✅ Actualización de balance desde Binance HABILITADA PARA PRUEBA")
                        current_balance_from_binance = self._calculate_current_balance_from_binance(self.binance_client)
                        self.current_balance = current_balance_from_binance
                        
                        # Calcular PnL total basado en la diferencia con el balance inicial
                        self.total_pnl = self.current_balance - self.initial_balance
                        
                        logger.info(f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f}")
                        logger.info(f"📊 PnL total calculado: ${self.total_pnl:.4f}")
                    
                    # Solo usar datos guardados si no hay cliente de Binance
                    if not self.binance_client and not self.position_history:
                        self.initial_balance = data.get('initial_balance', self.initial_balance)
                        self.current_balance = data.get('current_balance', self.current_balance)
                        self.total_pnl = data.get('total_pnl', 0.0)
                    
                logger.info(f"📂 Historial cargado: {len(self.position_history)} posiciones")
                logger.info(f"🤖 Estado de bots cargado: Conservative={self.bot_status['conservative']}, Aggressive={self.bot_status['aggressive']}")
                logger.info(f"📊 Posiciones activas cargadas: Conservative={len(self.active_positions['conservative'])}, Aggressive={len(self.active_positions['aggressive'])}")
            else:
                logger.info("📂 No se encontró archivo de historial, iniciando desde cero")
                # Estado por defecto: ambos bots inactivos
                self.bot_status = {
                    'conservative': False,
                    'aggressive': False
                }
                # Posiciones activas por defecto
                self.active_positions = {
                    'conservative': {},
                    'aggressive': {}
                }
                
                # Agregar bots plug and play a las posiciones activas
                from bot_registry import get_bot_registry
                bot_registry = get_bot_registry()
                for bot_name in bot_registry.get_all_bots().keys():
                    if bot_name not in ['conservative', 'aggressive']:
                        self.active_positions[bot_name] = {}
        except Exception as e:
            logger.error(f"❌ Error cargando historial: {e}")
            self.position_history = []
            # Estado por defecto en caso de error
            self.bot_status = {
                'conservative': False,
                'aggressive': False
            }
            # Posiciones activas por defecto en caso de error
            self.active_positions = {
                'conservative': {},
                'aggressive': {}
            }
            
            # Agregar bots plug and play a las posiciones activas
            from bot_registry import get_bot_registry
            bot_registry = get_bot_registry()
            for bot_name in bot_registry.get_all_bots().keys():
                if bot_name not in ['conservative', 'aggressive']:
                    self.active_positions[bot_name] = {}
    
    def save_history(self):
        """Guarda el historial de posiciones en archivo"""
        try:
            # HABILITADO PARA PRUEBA - FUNCIÓN PRINCIPAL
            logger.info("✅ save_history() HABILITADO PARA PRUEBA")
            
            # Crear carpeta logs si no existe
            os.makedirs("logs", exist_ok=True)

            # Escribir en archivos separados (nuevo formato)
            def _safe_write(path, payload):
                tmp_path = f"{path}.tmp"
                with open(tmp_path, 'w') as tf:
                    json.dump(payload, tf, indent=2, default=str)
                os.replace(tmp_path, path)

            # history.json (lista de órdenes)
            _safe_write(HISTORY_FILE_NEW, self.position_history)

            # active_positions.json (diccionario)
            _safe_write(ACTIVE_POS_FILE_NEW, self.active_positions)

            # account.json (saldos y pnl)
            account_payload = {
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_pnl': self.total_pnl,
                'last_updated': datetime.now().isoformat()
            }
            _safe_write(ACCOUNT_FILE_NEW, account_payload)

            # bot_status.json (estados)
            _safe_write(BOT_STATUS_FILE_NEW, self.bot_status)

            # (Deshabilitado) Escritura de archivo legado trading_history.json
            # Se mantiene solo el nuevo formato separado.
            
            # Log detallado del guardado del historial solo si cambió
            if len(self.position_history) > 0:
                last_trade = self.position_history[-1]
                
                # Solo loggear si el historial cambió
                if not hasattr(self, '_last_history_count') or self._last_history_count != len(self.position_history):
                    logger.info(f"💾 Historial guardado: {len(self.position_history)} posiciones")
                    self._last_history_count = len(self.position_history)
                
                # Solo loggear si el último trade cambió
                if not hasattr(self, '_last_trade_id') or self._last_trade_id != last_trade.get('order_id'):
                    logger.info(f"📈 Último trade: {last_trade['bot_type'].upper()} {last_trade['side']} - PnL: ${last_trade['net_pnl']:.4f}")
                    self._last_trade_id = last_trade.get('order_id')
                
                # Solo loggear si el balance cambió significativamente
                if not hasattr(self, '_last_balance_log') or abs(self.current_balance - self._last_balance_log) > 0.01:
                    logger.info(f"💰 Balance actualizado: ${self.current_balance:.2f} (PnL total: ${self.total_pnl:.4f})")
                    self._last_balance_log = self.current_balance
            else:
                # Solo loggear si el historial cambió
                if not hasattr(self, '_last_history_count') or self._last_history_count != len(self.position_history):
                    logger.info(f"💾 Historial guardado: {len(self.position_history)} posiciones")
                    self._last_history_count = len(self.position_history)
        except Exception as e:
            logger.error(f"❌ Error guardando historial: {e}")
    
    def calculate_stop_loss_take_profit(self, bot_type: str, signal: str, entry_price: float) -> tuple:
        """Calcula stop loss y take profit basado en el tipo de bot"""
        config = self.stop_loss_config.get(bot_type, self.stop_loss_config['demo'])
        
        if signal == 'BUY':
            stop_loss = entry_price * (1 - config['stop_loss'])
            take_profit = entry_price * (1 + config['take_profit'])
        else:  # SELL
            stop_loss = entry_price * (1 + config['stop_loss'])
            take_profit = entry_price * (1 - config['take_profit'])
        
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
            logger.info(f"🤖 Estado de bot {bot_type.upper()} actualizado: {'Activo' if is_active else 'Inactivo'}")
    
    def update_position(self, bot_type: str, signal: str, current_price: float, quantity: float = 1.0):
        """Actualiza las posiciones de un bot (soporta múltiples posiciones)"""
        
        # Si el bot cambió de señal de HOLD a BUY/SELL, abrir nueva posición
        if (signal in ['BUY', 'SELL'] and 
            self.last_signals[bot_type] == 'HOLD'):
            
            # Calcular comisión de entrada
            entry_fee = current_price * quantity * self.fee_rate
            
            # Calcular stop loss y take profit
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(bot_type, signal, current_price)
            
            # Crear ID único para la posición
            position_id = f"{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Abrir nueva posición
            self.positions[bot_type][position_id] = {
                'signal_type': signal,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': datetime.now(),
                'current_price': current_price,
                'entry_fee': entry_fee,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'pnl': 0.0,
                'pnl_pct': 0.0,
                'pnl_net': 0.0,
                'pnl_net_pct': 0.0
            }
            
            logger.info(f"🚀 {bot_type.upper()} - Nueva posición {signal} a ${current_price:.4f} (ID: {position_id})")
            
        # Si el bot cambió a HOLD, cerrar todas las posiciones abiertas
        elif (signal == 'HOLD' and 
              self.last_signals[bot_type] in ['BUY', 'SELL']):
            
            # Cerrar todas las posiciones abiertas del bot
            positions_to_close = list(self.positions[bot_type].keys())
            
            for position_id in positions_to_close:
                position = self.positions[bot_type][position_id]
            position['exit_price'] = current_price
            position['exit_time'] = datetime.now()
            position['current_price'] = current_price
            
            # Calcular comisión de salida
            exit_fee = current_price * position['quantity'] * self.fee_rate
            position['exit_fee'] = exit_fee
            total_fees = position['entry_fee'] + exit_fee
            
            # Calcular PnL bruto
            if position['signal_type'] == 'BUY':
                position['pnl'] = (current_price - position['entry_price']) * position['quantity']
                position['pnl_pct'] = ((current_price - position['entry_price']) / position['entry_price']) * 100
            else:  # SELL
                position['pnl'] = (position['entry_price'] - current_price) * position['quantity']
                position['pnl_pct'] = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                
                # Calcular PnL neto
                position['pnl_net'] = position['pnl'] - total_fees
                position['pnl_net_pct'] = (position['pnl_net'] / (position['entry_price'] * position['quantity'])) * 100
                position['total_fees'] = total_fees
                
                logger.info(f"🔒 {bot_type.upper()} - Cerrando posición {position_id}: PnL ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
                logger.info(f"📊 Trade completado: {position['signal_type']} {position['quantity']} DOGE - Precio entrada: ${position['entry_price']:.6f} - Precio salida: ${position['exit_price']:.6f}")
                logger.info(f"💵 PnL Neto: ${position['pnl_net']:.4f} - Comisiones: ${total_fees:.4f}")
                
                # Agregar al historial
                self.position_history.append({
                    'bot_type': bot_type,
                    'position_id': position_id,
                    **position
                })
                
                # Guardar historial inmediatamente cuando se cierra una posición
                # HABILITADO PARA PRUEBA
                logger.info("✅ save_history() HABILITADO PARA PRUEBA")
                self.save_history()
                
                # Actualizar saldo de cuenta
                self.update_balance(position['pnl_net'])
                
                # Remover posición activa
                del self.positions[bot_type][position_id]
        
        # Si tenemos posiciones abiertas, actualizar precios y PnL
        if self.positions[bot_type]:
            for position_id, position in self.positions[bot_type].items():
                position['current_price'] = current_price
                
                # Calcular PnL bruto actual
                if position['signal_type'] == 'BUY':
                    position['pnl'] = (current_price - position['entry_price']) * position['quantity']
                    position['pnl_pct'] = ((current_price - position['entry_price']) / position['entry_price']) * 100
                else:  # SELL
                    position['pnl'] = (position['entry_price'] - current_price) * position['quantity']
                    position['pnl_pct'] = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                
                # Calcular PnL neto estimado (solo comisión de entrada por ahora)
                estimated_exit_fee = current_price * position['quantity'] * self.fee_rate
                estimated_total_fees = position['entry_fee'] + estimated_exit_fee
                position['pnl_net'] = position['pnl'] - estimated_total_fees
                position['pnl_net_pct'] = (position['pnl_net'] / (position['entry_price'] * position['quantity'])) * 100
        
        # Actualizar última señal
        self.last_signals[bot_type] = signal
    
    def update_balance(self, pnl_net: float):
        """Actualiza el balance de la cuenta"""
        self.total_pnl += pnl_net
        self.current_balance = self.initial_balance + self.total_pnl
        
        logger.info(f"💰 Saldo actualizado: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.2f})")
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Obtiene información del saldo de la cuenta"""
        # Proteger contra división por cero
        if self.initial_balance > 0:
            balance_change_pct = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        else:
            balance_change_pct = 0.0
        
        # Obtener balances específicos de Binance si está disponible
        usdt_balance = 0.0
        doge_balance = 0.0
        
        if hasattr(self, 'binance_client') and self.binance_client:
            try:
                # Verificar si estamos usando margin trading
                leverage = int(os.getenv('LEVERAGE', '1'))
                
                if leverage > 1:
                    # Usar cuenta de margen
                    margin_account = self.binance_client.get_margin_account()
                    
                    # Buscar balances en la cuenta de margen
                    for asset in margin_account.get('userAssets', []):
                        if asset['asset'] == 'USDT':
                            usdt_balance = float(asset['free']) + float(asset['locked'])
                        elif asset['asset'] == 'DOGE':
                            doge_balance = float(asset['free']) + float(asset['locked'])
                else:
                    # Usar cuenta spot normal
                    account_info = self.binance_client.get_account()
                    balances = {balance['asset']: float(balance['free']) for balance in account_info['balances']}
                    usdt_balance = balances.get('USDT', 0.0)
                    doge_balance = balances.get('DOGE', 0.0)
                    
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener balance de Binance: {e}")
        
        # Obtener precio actual de DOGE
        doge_price = self._get_current_doge_price()
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_pnl': self.total_pnl,
            'balance_change_pct': balance_change_pct,
            'is_profitable': self.current_balance > self.initial_balance,
            'usdt_balance': usdt_balance,
            'doge_balance': doge_balance,
            'total_balance_usdt': usdt_balance + (doge_balance * doge_price),
            'doge_price': doge_price
        }
    
    def _get_current_doge_price(self) -> float:
        """Obtiene el precio actual de DOGE en USDT"""
        if hasattr(self, 'binance_client') and self.binance_client:
            try:
                ticker = self.binance_client.get_symbol_ticker(symbol='DOGEUSDT')
                return float(ticker['price'])
            except Exception as e:
                logger.warning(f"⚠️ No se pudo obtener precio de DOGE: {e}")
        return 0.0
    
    def get_position_info(self, bot_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de las posiciones actuales de un bot"""
        bot_positions = self.positions[bot_type]
        
        if not bot_positions:
            return None
        
        # Si solo hay una posición, devolverla directamente (compatibilidad con frontend)
        if len(bot_positions) == 1:
            return list(bot_positions.values())[0]
        
        # Si hay múltiples posiciones, devolver un resumen
        total_pnl = sum(pos['pnl'] for pos in bot_positions.values())
        total_pnl_net = sum(pos['pnl_net'] for pos in bot_positions.values())
        total_quantity = sum(pos['quantity'] for pos in bot_positions.values())
        
        # Usar la primera posición como base y agregar información de múltiples posiciones
        first_position = list(bot_positions.values())[0]
        
        return {
            **first_position,
            'multiple_positions': True,
            'position_count': len(bot_positions),
            'total_quantity': total_quantity,
            'total_pnl': total_pnl,
            'total_pnl_net': total_pnl_net,
            'all_positions': bot_positions
        }
    
    def get_all_positions(self) -> Dict[str, Any]:
        """Obtiene información de todas las posiciones (compatible con frontend)"""
        return {
            'conservative': self.get_position_info('conservative'),
            'aggressive': self.get_position_info('aggressive'),
            'last_signals': self.last_signals,
            'history': self.get_position_history(limit=20),
            'statistics': {
                'conservative': self.get_bot_statistics('conservative'),
                'aggressive': self.get_bot_statistics('aggressive'),
                'overall': self.get_bot_statistics()
            },
            'account_balance': self.get_account_balance()
        }
    
    def get_position_history(self, limit: int = 50) -> list:
        """Obtiene el historial de posiciones cerradas"""
        return self.position_history[-limit:] if self.position_history else []
    
    def get_bot_statistics(self, bot_type: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas de un bot específico o generales"""
        if bot_type:
            # Estadísticas de un bot específico
            bot_history = [pos for pos in self.position_history if pos.get('bot_type') == bot_type]
            
            if not bot_history:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'avg_pnl': 0.0,
                    'max_pnl': 0.0,
                    'min_pnl': 0.0
                }
            
            winning_trades = [pos for pos in bot_history if pos.get('pnl_net', 0) > 0]
            losing_trades = [pos for pos in bot_history if pos.get('pnl_net', 0) < 0]
            
            total_pnl = sum(pos.get('pnl_net', 0) for pos in bot_history)
            
            return {
                'total_trades': len(bot_history),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(bot_history)) * 100 if bot_history else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(bot_history) if bot_history else 0,
                'max_pnl': max(pos.get('pnl_net', 0) for pos in bot_history) if bot_history else 0,
                'min_pnl': min(pos.get('pnl_net', 0) for pos in bot_history) if bot_history else 0
            }
        else:
            # Estadísticas generales
            if not self.position_history:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'avg_pnl': 0.0,
                    'max_pnl': 0.0,
                    'min_pnl': 0.0
                }
            
            winning_trades = [pos for pos in self.position_history if pos.get('pnl_net', 0) > 0]
            losing_trades = [pos for pos in self.position_history if pos.get('pnl_net', 0) < 0]
            
            total_pnl = sum(pos.get('pnl_net', 0) for pos in self.position_history)
            
            return {
                'total_trades': len(self.position_history),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(self.position_history)) * 100 if self.position_history else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(self.position_history) if self.position_history else 0,
                'max_pnl': max(pos.get('pnl_net', 0) for pos in self.position_history) if self.position_history else 0,
                'min_pnl': min(pos.get('pnl_net', 0) for pos in self.position_history) if self.position_history else 0
            }
    
    def get_active_positions(self):
        """Retorna las posiciones activas"""
        return self.active_positions
    
    def update_active_position(self, bot_type: str, position_id: str, position_data: dict):
        """Actualiza una posición activa"""
        if bot_type in self.active_positions:
            self.active_positions[bot_type][position_id] = position_data
            logger.info(f"📊 Posición activa actualizada: {bot_type.upper()} - {position_id}")
    
    def remove_active_position(self, bot_type: str, position_id: str):
        """Remueve una posición activa"""
        if bot_type in self.active_positions and position_id in self.active_positions[bot_type]:
            del self.active_positions[bot_type][position_id]
            logger.info(f"📊 Posición activa removida: {bot_type.upper()} - {position_id}")
    
    def clear_active_positions(self, bot_type: str = None):
        """Limpia las posiciones activas de un bot específico o de todos"""
        if bot_type:
            if bot_type in self.active_positions:
                self.active_positions[bot_type] = {}
                logger.info(f"📊 Posiciones activas limpiadas para {bot_type.upper()}")
        else:
            self.active_positions = {
                'conservative': {},
                'aggressive': {}
            }
            
            # Agregar bots plug and play a las posiciones activas
            from bot_registry import get_bot_registry
            bot_registry = get_bot_registry()
            for bot_name in bot_registry.get_all_bots().keys():
                if bot_name not in ['conservative', 'aggressive']:
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
                if 'T' in dt_value:
                    return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
                else:
                    # Formato simple sin timezone
                    return datetime.fromisoformat(dt_value)
            except ValueError:
                logger.warning(f"⚠️ No se pudo parsear fecha: {dt_value}")
                return datetime.now()
        
        return datetime.now()

    def create_order_record(self, bot_type: str, symbol: str, side: str, quantity: float, 
                          entry_price: float, order_id: str, position_id: str) -> dict:
        """Crea un registro de orden en el historial"""
        order_record = {
            'order_id': order_id,
            'position_id': position_id,
            'bot_type': bot_type,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'status': 'OPEN',  # OPEN, UPDATED, CLOSED
            'current_price': entry_price,
            'pnl': 0.0,
            'pnl_percentage': 0.0,
            'close_price': None,
            'close_time': None,
            'duration_minutes': 0,
            'fees_paid': 0.0,
            'net_pnl': 0.0
        }
        
        # Agregar al historial
        self.position_history.append(order_record)
        logger.info(f"📝 Orden creada en historial: {bot_type.upper()} {side} {quantity} {symbol} a ${entry_price}")
        
        return order_record
    
    def update_order_status(self, order_id: str, current_price: float, status: str = 'UPDATED'):
        """Actualiza el estado de una orden en el historial"""
        for order in reversed(self.position_history):  # Buscar desde el más reciente
            if order['order_id'] == order_id:
                order['status'] = status
                order['current_price'] = current_price
                
                # Calcular PnL
                if order['side'] == 'BUY':
                    order['pnl'] = (current_price - order['entry_price']) * order['quantity']
                    order['pnl_percentage'] = ((current_price - order['entry_price']) / order['entry_price']) * 100
                else:  # SELL
                    order['pnl'] = (order['entry_price'] - current_price) * order['quantity']
                    order['pnl_percentage'] = ((order['entry_price'] - current_price) / order['entry_price']) * 100
                
                # Calcular duración
                if order['entry_time']:
                    entry_time = self._parse_datetime(order['entry_time'])
                    duration = datetime.now() - entry_time
                    order['duration_minutes'] = int(duration.total_seconds() / 60)
                
                logger.info(f"📊 Orden actualizada: {order['bot_type'].upper()} PnL: ${order['pnl']:.4f} ({order['pnl_percentage']:.2f}%)")
                return order
        
        logger.warning(f"⚠️ Orden {order_id} no encontrada en historial")
        return None
    
    def close_order(self, order_id: str, close_price: float, fees_paid: float = 0.0):
        """Cierra una orden en el historial con PnL final"""
        for order in reversed(self.position_history):  # Buscar desde el más reciente
            if order['order_id'] == order_id:
                order['status'] = 'CLOSED'
                order['close_price'] = close_price
                order['close_time'] = datetime.now()
                order['fees_paid'] = fees_paid
                
                # Calcular PnL final
                if order['side'] == 'BUY':
                    order['pnl'] = (close_price - order['entry_price']) * order['quantity']
                    order['pnl_percentage'] = ((close_price - order['entry_price']) / order['entry_price']) * 100
                else:  # SELL
                    order['pnl'] = (order['entry_price'] - close_price) * order['quantity']
                    order['pnl_percentage'] = ((order['entry_price'] - close_price) / order['entry_price']) * 100
                
                # PnL neto (después de comisiones)
                order['net_pnl'] = order['pnl'] - fees_paid
                
                # Calcular duración total
                if order['entry_time'] and order['close_time']:
                    entry_time = self._parse_datetime(order['entry_time'])
                    close_time = self._parse_datetime(order['close_time'])
                    duration = close_time - entry_time
                    order['duration_minutes'] = int(duration.total_seconds() / 60)
                
                # Actualizar balance y PnL total
                self.current_balance += order['net_pnl']
                self.total_pnl += order['net_pnl']
                
                # Guardar historial inmediatamente
                # HABILITADO PARA PRUEBA
                logger.info("✅ save_history() HABILITADO PARA PRUEBA")
                self.save_history()
                
                logger.info(f"🔒 Orden cerrada: {order['bot_type'].upper()} {order['side']} PnL: ${order['net_pnl']:.4f} ({order['pnl_percentage']:.2f}%)")
                logger.info(f"💰 Balance actualizado: ${self.current_balance:.2f} (PnL total: ${self.total_pnl:.4f})")
                
                return order
        
        logger.warning(f"⚠️ Orden {order_id} no encontrada en historial")
        return None
    
    def get_order_status(self, order_id: str) -> dict:
        """Obtiene el estado actual de una orden"""
        for order in reversed(self.position_history):
            if order['order_id'] == order_id:
                return order
        return None
    
    def get_open_orders(self) -> list:
        """Obtiene todas las órdenes abiertas (OPEN y UPDATED)"""
        return [order for order in self.position_history if order['status'] in ['OPEN', 'UPDATED']]
    
    def get_closed_orders(self) -> list:
        """Obtiene todas las órdenes cerradas"""
        return [order for order in self.position_history if order['status'] == 'CLOSED']
    
    def update_current_balance_from_binance(self):
        """Actualiza el balance actual desde Binance"""
        if not self.binance_client:
            return
        
        try:
            # Usar la función común para obtener balance
            new_balance = self._calculate_current_balance_from_binance(self.binance_client)
            
            # Actualizar balance actual
            self.current_balance = new_balance
            
            # Calcular PnL total basado en la diferencia con el balance inicial
            self.total_pnl = self.current_balance - self.initial_balance
            
            # Solo loggear si el balance cambió significativamente
            if not hasattr(self, '_last_balance_binance') or abs(self.current_balance - self._last_balance_binance) > 0.01:
                logger.info(f"💰 Balance actualizado desde Binance: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.4f})")
                self._last_balance_binance = self.current_balance
            
            return {
                'total_balance': new_balance,
                'total_pnl': self.total_pnl
            }
            
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
