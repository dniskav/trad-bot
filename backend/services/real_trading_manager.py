#!/usr/bin/env python3
"""
Sistema de Trading Real con Binance
Incluye validaciones de seguridad y límites de riesgo
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
from utils.colored_logger import get_colored_logger

# Cargar variables de entorno
load_dotenv('config_real_trading.env')

# Usar logger con colores
logger = get_colored_logger(__name__)

class RealTradingManager:
    """Gestor de trading real con validaciones de seguridad"""
    
    def __init__(self):
        # Configuración de API
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.trading_mode = os.getenv('TRADING_MODE', 'paper').lower()
        
        # Límites de seguridad
        self.max_position_size = float(os.getenv('MAX_POSITION_SIZE', '10.0'))
        self.max_daily_loss = float(os.getenv('MAX_DAILY_LOSS', '50.0'))
        self.enable_trading = os.getenv('ENABLE_TRADING', 'false').lower() == 'true'
        self.max_concurrent_positions_per_bot = int(os.getenv('MAX_CONCURRENT_POSITIONS_PER_BOT', '5'))
        
        # Configuración de apalancamiento
        self.leverage = int(os.getenv('LEVERAGE', '3'))  # Apalancamiento 3x por defecto
        self.margin_type = os.getenv('MARGIN_TYPE', 'CROSSED')  # Cross Margin por defecto
        
        # Inicializar cliente de Binance
        self.client = None
        if self.trading_mode == 'real' and self.api_key and self.secret_key:
            try:
                self.client = Client(self.api_key, self.secret_key)
                # Verificar conexión
                self.client.ping()
                logger.info("✅ Conexión a Binance establecida")
                logger.info(f"🔧 Modo de trading: {self.trading_mode}")
                logger.info(f"💰 Tamaño máximo por posición: ${self.max_position_size}")
                logger.info(f"📉 Pérdida máxima diaria: ${self.max_daily_loss}")
                logger.info(f"🔒 Trading habilitado: {self.enable_trading}")
                logger.info(f"⚡ Apalancamiento: {self.leverage}x")
                logger.info(f"🔄 Tipo de margen: {self.margin_type}")
            except Exception as e:
                logger.error(f"❌ Error conectando a Binance: {e}")
                self.client = None
        
        # Tracking de riesgo diario
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
        # Estado de activación de cada bot (por defecto inactivos)
        self.bot_status = {
            'conservative': False,  # Inactivo por defecto
            'aggressive': False     # Inactivo por defecto
        }
        
        # Posiciones activas por bot
        self.active_positions = {
            'conservative': {},
            'aggressive': {}
        }
        
        logger.info(f"🔧 Modo de trading: {self.trading_mode}")
        logger.info(f"💰 Tamaño máximo por posición: ${self.max_position_size}")
        logger.info(f"📉 Pérdida máxima diaria: ${self.max_daily_loss}")
        logger.info(f"🔒 Trading habilitado: {self.enable_trading}")
    
    def initialize_bot_status_from_tracker(self, trading_tracker):
        """Inicializa el estado de los bots desde el TradingTracker"""
        if trading_tracker and hasattr(trading_tracker, 'bot_status'):
            self.bot_status = trading_tracker.get_bot_status()
            logger.info(f"🤖 Estado de bots inicializado desde archivo: Conservative={self.bot_status['conservative']}, Aggressive={self.bot_status['aggressive']}")
        else:
            logger.info("🤖 Usando estado por defecto de bots: ambos inactivos")
    
    def initialize_active_positions_from_tracker(self, trading_tracker):
        """Inicializa las posiciones activas desde el TradingTracker"""
        if trading_tracker and hasattr(trading_tracker, 'get_active_positions'):
            saved_positions = trading_tracker.get_active_positions()
            self.active_positions = saved_positions
            conservative_count = len(self.active_positions['conservative'])
            aggressive_count = len(self.active_positions['aggressive'])
            logger.info(f"📊 Posiciones activas cargadas desde archivo: Conservative={conservative_count}, Aggressive={aggressive_count}")
        else:
            logger.info("📊 Usando posiciones activas por defecto: vacías")
    
    def sync_bot_status_with_tracker(self, trading_tracker):
        """Sincroniza el estado de los bots con el TradingTracker"""
        if trading_tracker and hasattr(trading_tracker, 'update_bot_status'):
            for bot_type, is_active in self.bot_status.items():
                trading_tracker.update_bot_status(bot_type, is_active)
    
    def sync_active_positions_with_tracker(self, trading_tracker):
        """Sincroniza las posiciones activas con el TradingTracker"""
        # HABILITADO PARA PRUEBA
        logger.info("✅ sync_active_positions_with_tracker() HABILITADO PARA PRUEBA")
        
        if trading_tracker and hasattr(trading_tracker, 'active_positions'):
            logger.info(f"🔄 Iniciando sync_active_positions_with_tracker")
            logger.info(f"📊 Active positions antes: {list(trading_tracker.active_positions.keys())}")
            
            # Preservar bots plug and play existentes
            plugin_bot_positions = {}
            for bot_name, positions in trading_tracker.active_positions.items():
                if bot_name not in ['conservative', 'aggressive']:
                    plugin_bot_positions[bot_name] = positions
                    logger.info(f"🔒 Preservando bot plug and play: {bot_name}")
            
            # Sincronizar solo bots legacy
            trading_tracker.active_positions = self.active_positions.copy()
            logger.info(f"📊 Active positions después de sync: {list(trading_tracker.active_positions.keys())}")
            
            # Restaurar bots plug and play
            for bot_name, positions in plugin_bot_positions.items():
                trading_tracker.active_positions[bot_name] = positions
                logger.info(f"🔄 Restaurando bot plug and play: {bot_name}")
            
            logger.info(f"📊 Active positions final: {list(trading_tracker.active_positions.keys())}")
            # HABILITADO PARA PRUEBA
            logger.info("✅ save_history() HABILITADO PARA PRUEBA")
            trading_tracker.save_history()
            logger.info("📊 Posiciones activas sincronizadas con el tracker (preservando bots plug and play)")
    
    def sync_with_binance_orders(self, trading_tracker=None):
        """Sincroniza las posiciones activas con las órdenes reales de Binance"""
        if not self.client:
            logger.warning("⚠️ Cliente de Binance no disponible para sincronización")
            return
        
        try:
            # Obtener todas las órdenes abiertas de Binance
            open_orders = self.client.get_open_orders(symbol='DOGEUSDT')
            binance_order_ids = {order['orderId'] for order in open_orders}
            
            # Verificar cada posición activa guardada
            positions_to_remove = []
            
            for bot_type in ['conservative', 'aggressive']:
                for position_id, position_data in self.active_positions[bot_type].items():
                    order_id = position_data.get('order_id')
                    
                    if order_id and order_id not in binance_order_ids:
                        # La orden ya no existe en Binance, remover la posición
                        positions_to_remove.append((bot_type, position_id))
                        logger.warning(f"⚠️ Posición {position_id} ya no existe en Binance, removiendo")
            
            # Remover posiciones que ya no existen en Binance y cerrar órdenes en historial
            for bot_type, position_id in positions_to_remove:
                position_data = self.active_positions[bot_type][position_id]
                order_id = position_data.get('order_id')
                
                # Cerrar la orden en el historial si existe
                if trading_tracker and order_id:
                    try:
                        # Obtener precio actual para calcular PnL final
                        current_price = self.get_current_price('DOGEUSDT')
                        if current_price:
                            # Calcular comisiones estimadas
                            trade_value = current_price * position_data.get('quantity', 0)
                            estimated_fees = trade_value * 0.001  # 0.1%
                            
                            # Cerrar la orden en el historial
                            trading_tracker.close_order(
                                order_id=order_id,
                                close_price=current_price,
                                fees_paid=estimated_fees
                            )
                            logger.info(f"🔒 Orden {order_id} cerrada en historial (posición removida de Binance)")
                    except Exception as e:
                        logger.error(f"❌ Error cerrando orden {order_id} en historial: {e}")
                
                # Remover de posiciones activas
                del self.active_positions[bot_type][position_id]
            
            if positions_to_remove:
                logger.info(f"🔄 {len(positions_to_remove)} posiciones obsoletas removidas")
                # Sincronizar con el tracker si está disponible
                if trading_tracker:
                    self.sync_active_positions_with_tracker(trading_tracker)
            else:
                logger.info("✅ Todas las posiciones activas están sincronizadas con Binance")
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando con Binance: {e}")
    
    def sync_history_with_binance_orders(self, trading_tracker=None):
        """Sincroniza el historial con las órdenes reales de Binance, cerrando órdenes que ya no existen"""
        # HABILITADO PARA PRUEBA
        logger.info("✅ sync_history_with_binance_orders() HABILITADO PARA PRUEBA")
        
        if not self.client or not trading_tracker:
            logger.warning("⚠️ Cliente de Binance o TradingTracker no disponible para sincronización del historial")
            return
        
        try:
            # Obtener todas las órdenes abiertas de Binance
            open_orders = self.client.get_open_orders(symbol='DOGEUSDT')
            binance_order_ids = {str(order['orderId']) for order in open_orders}
            
            # Obtener órdenes abiertas del historial
            history_open_orders = trading_tracker.get_open_orders()
            orders_to_close = []
            
            for order in history_open_orders:
                order_id = str(order.get('order_id', ''))
                
                # Saltar órdenes sintéticas - no se sincronizan con Binance
                if order.get('is_synthetic', False):
                    continue
                
                if order_id and order_id not in binance_order_ids:
                    # La orden ya no existe en Binance, debe cerrarse en el historial
                    orders_to_close.append(order)
                    logger.warning(f"⚠️ Orden {order_id} ya no existe en Binance, cerrando en historial")
            
            # Cerrar las órdenes que ya no existen en Binance
            for order in orders_to_close:
                order_id = str(order['order_id'])
                position_id = order.get('position_id', '')
                bot_type = order.get('bot_type', '')
                
                try:
                    # Obtener precio actual para calcular PnL final
                    current_price = self.get_current_price('DOGEUSDT')
                    if current_price:
                        # Calcular comisiones estimadas
                        trade_value = current_price * order.get('quantity', 0)
                        estimated_fees = trade_value * 0.001  # 0.1%
                        
                        # Cerrar la orden en el historial
                        trading_tracker.close_order(
                            order_id=order_id,
                            close_price=current_price,
                            fees_paid=estimated_fees
                        )
                        logger.info(f"🔒 Orden {order_id} cerrada en historial (no existe en Binance)")
                        
                        # Remover de posiciones activas si existe
                        if position_id and bot_type and bot_type in self.active_positions:
                            if position_id in self.active_positions[bot_type]:
                                del self.active_positions[bot_type][position_id]
                                logger.info(f"🗑️ Posición {position_id} removida de posiciones activas")
                        
                except Exception as e:
                    logger.error(f"❌ Error cerrando orden {order_id} en historial: {e}")
            
            if orders_to_close:
                logger.info(f"🔄 {len(orders_to_close)} órdenes del historial cerradas automáticamente")
                # Sincronizar posiciones activas con el tracker después de cerrar órdenes
                if trading_tracker:
                    self.sync_active_positions_with_tracker(trading_tracker)
            else:
                logger.info("✅ Historial sincronizado con órdenes de Binance")
                # Asegurar que los bots plug and play se preserven incluso cuando no hay órdenes que cerrar
                if trading_tracker:
                    self.sync_active_positions_with_tracker(trading_tracker)
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando historial con Binance: {e}")
    
    def update_all_orders_status(self, trading_tracker=None):
        """Actualiza el estado de todas las órdenes abiertas con el precio actual"""
        if not self.client or not trading_tracker:
            return
        
        try:
            # Obtener precio actual
            ticker = self.client.get_symbol_ticker(symbol='DOGEUSDT')
            current_price = float(ticker['price'])
            
            # Actualizar todas las órdenes abiertas (excepto sintéticas)
            open_orders = trading_tracker.get_open_orders()
            for order in open_orders:
                # Saltar órdenes sintéticas - no se actualizan con precio de Binance
                if order.get('is_synthetic', False):
                    continue
                    
                trading_tracker.update_order_status(
                    order_id=order['order_id'],
                    current_price=current_price,
                    status='UPDATED'
                )
            
            if open_orders:
                logger.info(f"📊 {len(open_orders)} órdenes abiertas actualizadas con precio ${current_price}")
                
        except Exception as e:
            logger.error(f"❌ Error actualizando estado de órdenes: {e}")
    
    def check_and_close_positions(self, trading_tracker=None, current_price=None):
        """Verifica si alguna posición debe cerrarse por take profit o stop loss"""
        if not trading_tracker or not current_price:
            return
        
        try:
            # Obtener todas las órdenes abiertas
            open_orders = trading_tracker.get_open_orders()
            
            for order in open_orders:
                order_id = order['order_id']
                bot_type = order['bot_type']
                side = order['side']
                entry_price = order['entry_price']
                quantity = order['quantity']
                is_synthetic = order.get('is_synthetic', False)
                
                # Calcular PnL actual
                if side == 'BUY':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # SELL
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                # Obtener configuración de stop loss y take profit
                stop_loss, take_profit = trading_tracker.calculate_stop_loss_take_profit(
                    bot_type, side, entry_price
                )
                
                # Verificar si debe cerrar por take profit o stop loss
                should_close = False
                close_reason = ""
                
                if side == 'BUY':
                    if current_price >= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                    elif current_price <= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                else:  # SELL
                    if current_price <= take_profit:
                        should_close = True
                        close_reason = "Take Profit"
                    elif current_price >= stop_loss:
                        should_close = True
                        close_reason = "Stop Loss"
                
                if should_close:
                    if is_synthetic:
                        logger.info(f"🧪 {bot_type.upper()} - Cerrando posición sintética por {close_reason}: ${entry_price:.5f} → ${current_price:.5f} ({pnl_pct:.2f}%)")
                    else:
                        logger.info(f"🎯 {bot_type.upper()} - Cerrando posición por {close_reason}: ${entry_price:.5f} → ${current_price:.5f} ({pnl_pct:.2f}%)")
                    
                    # Cerrar la posición
                    self.close_position_with_tracking(
                        bot_type=bot_type,
                        position_id=order['position_id'],
                        trading_tracker=trading_tracker
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error verificando cierre de posiciones: {e}")
    
    def close_position_with_tracking(self, bot_type: str, position_id: str, trading_tracker=None):
        """Cierra una posición y actualiza el tracking en el historial"""
        if bot_type not in self.active_positions or position_id not in self.active_positions[bot_type]:
            logger.warning(f"⚠️ Posición {position_id} no encontrada en {bot_type}")
            return False
        
        position = self.active_positions[bot_type][position_id]
        order_id = str(position['order_id'])
        
        try:
            # Obtener precio actual para cerrar
            ticker = self.client.get_symbol_ticker(symbol=position['symbol'])
            close_price = float(ticker['price'])
            
            # Calcular comisiones estimadas (0.1% de Binance)
            trade_value = close_price * position['quantity']
            estimated_fees = trade_value * 0.001  # 0.1%
            
            # Cerrar la orden en el historial
            if trading_tracker and hasattr(trading_tracker, 'close_order'):
                trading_tracker.close_order(
                    order_id=order_id,
                    close_price=close_price,
                    fees_paid=estimated_fees
                )
            
            # Remover de posiciones activas
            del self.active_positions[bot_type][position_id]
            
            # Sincronizar con tracker
            if trading_tracker:
                self.sync_active_positions_with_tracker(trading_tracker)
            
            logger.info(f"🔒 Posición cerrada: {bot_type.upper()} {position_id} a ${close_price}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error cerrando posición {position_id}: {e}")
            return False
    
    def reset_daily_tracking(self):
        """Reinicia el tracking diario si es un nuevo día"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = today
            logger.info("🔄 Tracking diario reiniciado")
    
    def check_risk_limits(self, trade_amount: float, bot_type: str) -> Dict[str, Any]:
        """Verifica límites de riesgo antes de hacer un trade"""
        self.reset_daily_tracking()
        
        checks = {
            'can_trade': True,
            'reasons': []
        }
        
        # Verificar si el trading está habilitado
        if not self.enable_trading:
            checks['can_trade'] = False
            checks['reasons'].append("Trading deshabilitado en configuración")
        
        # Verificar límite de pérdida diaria
        if self.daily_pnl <= -self.max_daily_loss:
            checks['can_trade'] = False
            checks['reasons'].append(f"Límite de pérdida diaria alcanzado: ${self.daily_pnl:.2f}")
        
        # Verificar tamaño de posición (considerando apalancamiento)
        leverage_multiplier = self.leverage if self.leverage > 1 else 1.0
        max_position_size_with_leverage = self.max_position_size * leverage_multiplier
        position_tolerance = 0.001  # 0.1 centavos de tolerancia para errores de precisión
        
        if trade_amount > max_position_size_with_leverage + position_tolerance:
            checks['can_trade'] = False
            difference = trade_amount - max_position_size_with_leverage
            checks['reasons'].append(f"Tamaño de posición excede límite: ${trade_amount:.6f} > ${max_position_size_with_leverage:.6f} (diferencia: ${difference:.6f})")
        
        # Verificar número de posiciones concurrentes con redistribución dinámica
        bot_positions = len(self.active_positions.get(bot_type, {}))
        
        # Calcular límite dinámico basado en bots activos
        total_max_positions = self.max_concurrent_positions_per_bot * 2  # Total para ambos bots
        active_bots = sum(1 for status in self.bot_status.values() if status)
        
        if active_bots > 0:
            # Redistribuir posiciones disponibles entre bots activos
            available_positions_per_bot = total_max_positions // active_bots
            dynamic_limit = available_positions_per_bot
        else:
            dynamic_limit = 0
        
        if bot_positions >= dynamic_limit:
            checks['can_trade'] = False
            if active_bots == 1:
                checks['reasons'].append(f"Máximo de posiciones concurrentes alcanzado para {bot_type}: {bot_positions}/{dynamic_limit} (usando todas las posiciones disponibles)")
            else:
                checks['reasons'].append(f"Máximo de posiciones concurrentes alcanzado para {bot_type}: {bot_positions}/{dynamic_limit}")
        
        return checks
    
    def get_account_balance(self) -> Dict[str, float]:
        """Obtiene el balance de la cuenta"""
        if not self.client:
            return {'USDT': 0.0, 'error': 'Cliente no inicializado'}
        
        try:
            account = self.client.get_account()
            balances = {}
            for balance in account['balances']:
                if float(balance['free']) > 0:
                    balances[balance['asset']] = float(balance['free'])
            return balances
        except Exception as e:
            logger.error(f"❌ Error obteniendo balance: {e}")
            return {'error': str(e)}
    
    def is_trading_enabled(self) -> bool:
        """Verifica si el trading está habilitado"""
        return self.enable_trading and self.trading_mode == 'real' and self.client is not None
    
    def check_balance_availability(self, signal: str, bot_type: str, current_price: float) -> Dict[str, Any]:
        """Verifica si hay balance suficiente para la operación solicitada"""
        
        # Obtener balance actual - usar cuenta margin si el apalancamiento está habilitado
        if self.leverage > 1:
            # Usar cuenta de margen
            margin_account = self.client.get_margin_account()
            
            # Buscar balances en la cuenta de margen
            usdt_balance = 0.0
            doge_balance = 0.0
            
            for asset in margin_account.get('userAssets', []):
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['free']) + float(asset['locked'])
                elif asset['asset'] == 'DOGE':
                    doge_balance = float(asset['free']) + float(asset['locked'])
            
            logger.info(f"💰 Balance disponible (Margin): {usdt_balance:.2f} USDT, {doge_balance:.2f} DOGE")
            logger.info(f"⚡ Apalancamiento: {self.leverage}x - Poder de trading: ${usdt_balance * self.leverage:.2f} USDT")
        else:
            # Usar cuenta spot normal
            account_info = self.client.get_account()
            balances = {balance['asset']: float(balance['free']) for balance in account_info['balances']}
            
            usdt_balance = balances.get('USDT', 0.0)
            doge_balance = balances.get('DOGE', 0.0)
            
            logger.info(f"💰 Balance disponible (Spot): {usdt_balance:.2f} USDT, {doge_balance:.2f} DOGE")
        
        if signal == 'BUY':
            # Calcular cantidad necesaria en USDT (considerando apalancamiento)
            leverage_multiplier = self.leverage if self.leverage > 1 else 1.0
            
            max_position_with_leverage = self.max_position_size * leverage_multiplier
            
            if bot_type == 'conservative':
                base_usdt = min(max(1.0, usdt_balance * 0.1), self.max_position_size)
                required_usdt = min(base_usdt * leverage_multiplier, max_position_with_leverage)
            else:  # aggressive
                base_usdt = min(max(1.0, usdt_balance * 0.15), self.max_position_size)
                required_usdt = min(base_usdt * leverage_multiplier, max_position_with_leverage)
            
            # Verificar disponibilidad
            if usdt_balance < required_usdt:
                available_usdt = usdt_balance * 0.9  # Usar 90% del disponible
                if available_usdt < 1.0:
                    return {
                        'can_trade': False,
                        'reason': f'Saldo USDT insuficiente: {usdt_balance:.2f} USDT < $1.00 mínimo',
                        'available_usdt': usdt_balance,
                        'required_usdt': required_usdt
                    }
                else:
                    return {
                        'can_trade': True,
                        'adjusted': True,
                        'available_usdt': available_usdt,
                        'required_usdt': required_usdt,
                        'message': f'Ajustando cantidad: ${available_usdt:.2f} (90% del disponible)'
                    }
            else:
                return {
                    'can_trade': True,
                    'adjusted': False,
                    'available_usdt': required_usdt,
                    'required_usdt': required_usdt
                }
        
        else:  # SELL
            # Calcular cantidad necesaria en DOGE (considerando apalancamiento)
            leverage_multiplier = self.leverage if self.leverage > 1 else 1.0
            max_position_with_leverage = self.max_position_size * leverage_multiplier
            max_doge_value = max_position_with_leverage / current_price
            min_doge_for_profit = 1.0  # Mínimo 1.0 DOGE para operaciones rentables
            
            if bot_type == 'conservative':
                base_doge = min(max(min_doge_for_profit, doge_balance * 0.1), max_doge_value)
                required_doge = min(base_doge * leverage_multiplier, max_doge_value)
            else:  # aggressive
                base_doge = min(max(min_doge_for_profit, doge_balance * 0.15), max_doge_value)
                required_doge = min(base_doge * leverage_multiplier, max_doge_value)
            
            # Verificar disponibilidad
            if doge_balance < required_doge:
                available_doge = max(1.0, doge_balance * 0.9)  # Usar 90% del disponible, mínimo 1.0 DOGE
                if available_doge < 1.0:  # Mínimo 1.0 DOGE para operaciones rentables
                    return {
                        'can_trade': False,
                        'reason': f'Saldo DOGE insuficiente: {doge_balance:.2f} DOGE < 1.0 mínimo',
                        'available_doge': doge_balance,
                        'required_doge': required_doge
                    }
                else:
                    return {
                        'can_trade': True,
                        'adjusted': True,
                        'available_doge': available_doge,
                        'required_doge': required_doge,
                        'message': f'Ajustando cantidad: {available_doge:.2f} DOGE (90% del disponible)'
                    }
            else:
                return {
                    'can_trade': True,
                    'adjusted': False,
                    'available_doge': required_doge,
                    'required_doge': required_doge
                }

    def place_order(self, bot_type: str, signal: str, current_price: float, trading_tracker=None) -> Dict[str, Any]:
        """Coloca una orden real para un bot específico"""
        symbol = 'DOGEUSDT'  # Símbolo fijo para nuestros bots (NOTIONAL mínimo $1.00)
        
        # Verificar si el bot está activo
        if not self.is_bot_active(bot_type):
            logger.info(f"ℹ️ {bot_type.upper()} - Bot desactivado, ignorando señal: {signal}")
            return {
                'success': False,
                'error': f'Bot {bot_type} está desactivado',
                'bot_status': 'inactive'
            }
        
        # Verificar disponibilidad de balance ANTES de intentar la operación
        balance_check = self.check_balance_availability(signal, bot_type, current_price)
        
        if not balance_check['can_trade']:
            logger.warning(f"⚠️ {bot_type.upper()} - {balance_check['reason']}")
            return {
                'success': False,
                'error': balance_check['reason'],
                'balance_check': balance_check
            }
        
        # Si se ajustó la cantidad, mostrar mensaje
        if balance_check.get('adjusted', False):
            logger.info(f"📊 {bot_type.upper()} - {balance_check['message']}")
        
        # Calcular cantidad basada en la verificación de balance
        if signal == 'BUY':
            # Usar la cantidad ajustada si fue necesario
            quantity_usdt = balance_check.get('available_usdt', balance_check['required_usdt'])
            quantity_doge = quantity_usdt / current_price
            
        else:  # SELL
            # Usar la cantidad ajustada si fue necesario
            quantity_doge = balance_check.get('available_doge', balance_check['required_doge'])
        
        # Ajustar precisión para DOGE (mínimo 4 DOGE, máximo 2 decimales)
        quantity_doge = max(4.0, round(quantity_doge, 2))
        
        # Verificar que la cantidad sea válida para Binance
        if quantity_doge < 4.0:
            logger.warning(f"⚠️ {bot_type.upper()} - Cantidad muy pequeña: {quantity_doge} DOGE, usando mínimo 4 DOGE")
            quantity_doge = 4.0
        
        # Ejecutar trade
        result = self.execute_trade(symbol, signal, current_price, quantity_doge, bot_type, trading_tracker)
        
        if result['success']:
            logger.info(f"✅ {bot_type.upper()} - Trade ejecutado: {signal} {quantity_doge} DOGE a ${current_price}")
        else:
            logger.error(f"❌ {bot_type.upper()} - Error en trade: {result.get('error', 'Error desconocido')}")
        
        return result
    
    def execute_trade(self, symbol: str, signal: str, current_price: float, quantity: float = None, bot_type: str = 'conservative', trading_tracker=None) -> Dict[str, Any]:
        """Ejecuta un trade basado en la señal del bot"""
        
        if signal not in ['BUY', 'SELL']:
            return {
                'success': False,
                'error': f'Señal inválida: {signal}'
            }
        
        # Calcular cantidad si no se proporciona
        if quantity is None:
            # Usar 10% del balance disponible o máximo permitido
            balance = self.get_account_balance()
            usdt_balance = balance.get('USDT', 0.0)
            quantity = min(usdt_balance * 0.1, self.max_position_size) / current_price
        
        # Determinar lado de la orden
        side = 'BUY' if signal == 'BUY' else 'SELL'
        
        # Ejecutar trade
        result = self.place_order_raw(symbol, side, quantity, bot_type)
        
        if result['success']:
            # Registrar posición activa para el bot específico
            position_id = f"{symbol}_{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            order_id = result['order']['orderId']
            
            self.active_positions[bot_type][position_id] = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': current_price,
                'entry_time': datetime.now(),
                'order_id': order_id
            }
            
            # Crear registro de orden en el historial si hay trading_tracker
            if trading_tracker and hasattr(trading_tracker, 'create_order_record'):
                trading_tracker.create_order_record(
                    bot_type=bot_type,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    entry_price=current_price,
                    order_id=str(order_id),
                    position_id=position_id
                )
            
            # Sincronizar con el tracker si está disponible
            if trading_tracker:
                self.sync_active_positions_with_tracker(trading_tracker)
            
            logger.info(f"📊 Posición registrada para {bot_type}: {position_id}")
        
        return result
    
    def place_order_raw(self, symbol: str, side: str, quantity: float, bot_type: str = 'conservative', order_type: str = 'MARKET') -> Dict[str, Any]:
        """Coloca una orden real en Binance"""
        
        if not self.client:
            return {
                'success': False,
                'error': 'Cliente de Binance no inicializado'
            }
        
        try:
            # Obtener precio actual para cálculos
            current_price = self.get_current_price(symbol)
            if not current_price:
                return {
                    'success': False,
                    'error': 'No se pudo obtener el precio actual'
                }
            
            # Verificar límites de riesgo (convertir cantidad a valor USD)
            trade_value_usd = quantity * current_price
            risk_check = self.check_risk_limits(trade_value_usd, bot_type)
            if not risk_check['can_trade']:
                logger.warning(f"⚠️ Trade bloqueado: {', '.join(risk_check['reasons'])}")
                return {
                    'success': False,
                    'error': 'Trade bloqueado por límites de riesgo',
                    'reasons': risk_check['reasons']
                }
            
            # Verificar margin level si usamos apalancamiento
            if self.trading_mode == 'real' and self.leverage > 1:
                if not self.check_margin_safety():
                    logger.warning("⚠️ Trade bloqueado: Margin level muy bajo")
                    return {
                        'success': False,
                        'error': 'Margin level muy bajo para operar con apalancamiento'
                }
            
            # Obtener información del símbolo para validar cantidad
            symbol_info = self.client.get_symbol_info(symbol)
            lot_size_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'),
                None
            )
            
            if lot_size_filter:
                min_qty = float(lot_size_filter['minQty'])
                max_qty = float(lot_size_filter['maxQty'])
                step_size = float(lot_size_filter['stepSize'])
                
                # Ajustar cantidad según step size
                quantity = round(quantity / step_size) * step_size
                quantity = max(min_qty, min(max_qty, quantity))
                
                # Asegurar que la cantidad tenga la precisión correcta
                if step_size >= 1.0:
                    quantity = int(quantity)  # Para step_size >= 1, usar enteros
                else:
                    # Para step_size < 1, calcular decimales correctos
                    decimals = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
                    quantity = round(quantity, decimals)
            
            # Verificar filtro NOTIONAL (valor mínimo de la orden)
            notional_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'NOTIONAL'),
                None
            )
            
            if notional_filter:
                min_notional = float(notional_filter['minNotional'])
                current_notional = quantity * current_price
                
                if current_notional < min_notional:
                    # Ajustar cantidad para cumplir con el mínimo notional
                    quantity = min_notional / current_price
                    if lot_size_filter:
                        step_size = float(lot_size_filter['stepSize'])
                        # Redondear hacia arriba para asegurar que cumple NOTIONAL
                        quantity = round(quantity / step_size) * step_size
                        
                        # Verificar que el NOTIONAL final cumple el mínimo
                        final_notional = quantity * current_price
                        if final_notional < min_notional:
                            # Si no cumple, agregar un step más
                            quantity += step_size
                        
                        if step_size >= 1.0:
                            quantity = int(quantity)
                        else:
                            decimals = len(str(step_size).split('.')[-1]) if '.' in str(step_size) else 0
                            quantity = round(quantity, decimals)
                    
                    logger.info(f"📊 Ajustando cantidad para cumplir NOTIONAL mínimo: {quantity} {symbol}")
            
            # Colocar orden con apalancamiento (Margin Trading)
            if self.trading_mode == 'real' and self.leverage > 1:
                # Usar órdenes de margen con apalancamiento
                order = self.client.create_margin_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    sideEffectType='MARGIN_BUY' if side == 'BUY' else 'AUTO_REPAY'
                )
                logger.info(f"⚡ Orden de margen ejecutada ({self.leverage}x): {side} {quantity} {symbol}")
            else:
                # Usar órdenes normales (sin apalancamiento)
                order = self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity
                )
                logger.info(f"✅ Orden ejecutada: {side} {quantity} {symbol}")
                logger.info(f"   Order ID: {order['orderId']}")
                logger.info(f"   Precio: ${order.get('fills', [{}])[0].get('price', 'N/A')}")
                
                # Actualizar tracking
                self.daily_trades += 1
            
            return {
                'success': True,
                'order': order,
                'quantity': quantity,
                'symbol': symbol,
                'side': side
            }
            
        except BinanceAPIException as e:
            logger.error(f"❌ Error de API Binance: {e}")
            return {
                'success': False,
                'error': f'Error de API: {e.message}',
                'code': e.code
            }
        except Exception as e:
            logger.error(f"❌ Error inesperado: {e}")
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def close_position(self, position_id: str, bot_type: str) -> Dict[str, Any]:
        """Cierra una posición específica de un bot"""
        if bot_type not in self.active_positions or position_id not in self.active_positions[bot_type]:
            return {
                'success': False,
                'error': 'Posición no encontrada'
            }
        
        position = self.active_positions[bot_type][position_id]
        
        # Determinar lado opuesto para cerrar
        close_side = 'SELL' if position['side'] == 'BUY' else 'BUY'
        
        # Ejecutar orden de cierre
        result = self.place_order_raw(
            position['symbol'],
            close_side,
            position['quantity'],
            bot_type
        )
        
        if result['success']:
            # Calcular PnL
            exit_price = float(result['order'].get('fills', [{}])[0].get('price', position['entry_price']))
            
            if position['side'] == 'BUY':
                pnl = (exit_price - position['entry_price']) * position['quantity']
            else:
                pnl = (position['entry_price'] - exit_price) * position['quantity']
            
            # Actualizar tracking diario
            self.daily_pnl += pnl
            
            # Remover posición activa
            del self.active_positions[bot_type][position_id]
            
            logger.info(f"🔒 Posición cerrada para {bot_type}: {position_id}")
            logger.info(f"   PnL: ${pnl:.4f}")
            logger.info(f"   PnL Diario: ${self.daily_pnl:.4f}")
            
            result['pnl'] = pnl
            result['exit_price'] = exit_price
        
        return result
    
    def get_trading_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del sistema de trading"""
        self.reset_daily_tracking()
        
        balance = self.get_account_balance()
        
        # Calcular posiciones totales por bot
        conservative_positions = len(self.active_positions.get('conservative', {}))
        aggressive_positions = len(self.active_positions.get('aggressive', {}))
        total_positions = conservative_positions + aggressive_positions
        
        return {
            'trading_mode': self.trading_mode,
            'trading_enabled': self.enable_trading,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'active_positions': {
                'conservative': conservative_positions,
                'aggressive': aggressive_positions,
                'total': total_positions
            },
            'max_positions_per_bot': self.max_concurrent_positions_per_bot,
            'max_daily_loss': self.max_daily_loss,
            'remaining_daily_loss': self.max_daily_loss + self.daily_pnl,
            'account_balance': balance,
            'risk_status': 'OK' if self.daily_pnl > -self.max_daily_loss else 'LIMIT_REACHED',
            'bot_status': self.bot_status,
            'dynamic_limits': self.get_dynamic_position_limits()
        }
    
    def is_bot_active(self, bot_type: str) -> bool:
        """Verifica si un bot está activo"""
        return self.bot_status.get(bot_type, False)
    
    def activate_bot(self, bot_type: str, trading_tracker=None) -> bool:
        """Activa un bot"""
        if bot_type in self.bot_status:
            self.bot_status[bot_type] = True
            logger.info(f"✅ Bot {bot_type.upper()} activado")
            
            # Sincronizar con TradingTracker si está disponible
            if trading_tracker and hasattr(trading_tracker, 'update_bot_status'):
                trading_tracker.update_bot_status(bot_type, True)
            
            return True
        return False
    
    def deactivate_bot(self, bot_type: str, trading_tracker=None) -> bool:
        """Desactiva un bot y cierra todas sus posiciones"""
        if bot_type not in self.bot_status:
            return False
            
        if not self.bot_status[bot_type]:
            logger.info(f"ℹ️ Bot {bot_type.upper()} ya está desactivado")
            return True
            
        # Cerrar todas las posiciones del bot antes de desactivarlo
        positions_to_close = list(self.active_positions[bot_type].keys())
        if positions_to_close:
            logger.info(f"🔄 Cerrando {len(positions_to_close)} posiciones del bot {bot_type.upper()}...")
            
            for position_id in positions_to_close:
                try:
                    self.close_position_with_tracking(bot_type, position_id, trading_tracker)
                    logger.info(f"✅ Posición {position_id} cerrada exitosamente")
                except Exception as e:
                    logger.error(f"❌ Error cerrando posición {position_id}: {e}")
        
        # Desactivar el bot
        self.bot_status[bot_type] = False
        logger.info(f"🔴 Bot {bot_type.upper()} desactivado")
        
        # Sincronizar con TradingTracker si está disponible
        if trading_tracker and hasattr(trading_tracker, 'update_bot_status'):
            trading_tracker.update_bot_status(bot_type, False)
            # Sincronizar posiciones activas después de cerrar todas las posiciones
            self.sync_active_positions_with_tracker(trading_tracker)
        
        return True
    
    def get_dynamic_position_limits(self) -> Dict[str, Any]:
        """Obtiene información sobre los límites dinámicos de posiciones"""
        total_max_positions = self.max_concurrent_positions_per_bot * 2
        active_bots = sum(1 for status in self.bot_status.values() if status)
        
        if active_bots > 0:
            available_positions_per_bot = total_max_positions // active_bots
        else:
            available_positions_per_bot = 0
        
        return {
            'total_max_positions': total_max_positions,
            'active_bots': active_bots,
            'available_positions_per_bot': available_positions_per_bot,
            'bot_status': self.bot_status,
            'current_positions': {
                'conservative': len(self.active_positions.get('conservative', {})),
                'aggressive': len(self.active_positions.get('aggressive', {}))
            }
        }
    
    def get_margin_level(self) -> Dict[str, Any]:
        """Obtiene información detallada del margen"""
        if not self.client:
            return {'success': False, 'error': 'Cliente no inicializado'}
        
        try:
            margin_account = self.client.get_margin_account()
            margin_level = float(margin_account.get('marginLevel', 0))
            
            # Calcular fondos disponibles para trading
            usdt_balance = 0.0
            doge_balance = 0.0
            
            for asset in margin_account.get('userAssets', []):
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['free']) + float(asset['locked'])
                elif asset['asset'] == 'DOGE':
                    doge_balance = float(asset['free']) + float(asset['locked'])
            
            # Obtener precio actual de DOGE
            ticker = self.client.get_symbol_ticker(symbol='DOGEUSDT')
            doge_price = float(ticker['price'])
            
            # Calcular fondos totales disponibles
            total_available_usdt = usdt_balance + (doge_balance * doge_price)
            
            # Con apalancamiento, los fondos disponibles para trading son mayores
            leverage = self.leverage
            trading_power = total_available_usdt * leverage
            
            return {
                'success': True,
                'margin_level': margin_level,
                'leverage': leverage,
                'margin_type': self.margin_type,
                'total_net_asset': margin_account.get('totalNetAssetOfBtc', 0),
                'total_liability': margin_account.get('totalLiabilityOfBtc', 0),
                'account_equity': margin_account.get('totalNetAssetOfBtc', 0),
                'usdt_balance': usdt_balance,
                'doge_balance': doge_balance,
                'doge_price': doge_price,
                'total_available_usdt': total_available_usdt,
                'trading_power_usdt': trading_power,
                'margin_ratio': 1.0 / leverage if leverage > 0 else 0,
                'is_safe': margin_level > 2.0  # Consideramos seguro si margin level > 2.0
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo margin level: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_margin_safety(self) -> bool:
        """Verifica si el margin level es seguro (mayor a 2.0)"""
        margin_info = self.get_margin_level()
        if not margin_info['success']:
            return False
        
        margin_level = margin_info['margin_level']
        is_safe = margin_level > 2.0
        
        if not is_safe:
            logger.warning(f"⚠️ Margin level bajo: {margin_level:.2f} (límite seguro: 2.0)")
        
        return is_safe
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Obtiene el precio actual de un símbolo"""
        try:
            if not self.client:
                return None
            
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"❌ Error obteniendo precio de {symbol}: {e}")
            return None

# Instancia global del gestor de trading real
real_trading_manager = RealTradingManager()