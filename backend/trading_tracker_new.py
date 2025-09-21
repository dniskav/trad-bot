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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Archivo para persistir el historial
HISTORY_FILE = "logs/trading_history.json"
BACKUP_FILE = "logs/trading_history_backup.json"

class TradingTracker:
    """Rastrea las posiciones de trading en tiempo real - Soporta múltiples posiciones por bot"""
    
    def __init__(self, binance_client=None):
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
        
        # Stop Loss y Take Profit recomendados por tipo de bot
        self.stop_loss_config = {
            'conservative': {'stop_loss': 0.015, 'take_profit': 0.020},  # 1.5% SL, 2.0% TP
            'aggressive': {'stop_loss': 0.008, 'take_profit': 0.012},   # 0.8% SL, 1.2% TP
            'demo': {'stop_loss': 0.010, 'take_profit': 0.015}           # 1.0% SL, 1.5% TP
        }
    
    def _calculate_initial_balance_from_binance(self, binance_client):
        """Calcula el balance inicial desde Binance (USDT + ADA convertido a USDT)"""
        if not binance_client:
            logger.warning("⚠️ Cliente de Binance no disponible, usando balance por defecto: $10.00")
            return 10.0
        
        try:
            # Obtener balance de la cuenta
            account_info = binance_client.get_account()
            balances = {balance['asset']: float(balance['free']) for balance in account_info['balances']}
            
            usdt_balance = balances.get('USDT', 0.0)
            ada_balance = balances.get('ADA', 0.0)
            
            # Obtener precio actual de ADA para convertir a USDT
            ticker = binance_client.get_symbol_ticker(symbol='ADAUSDT')
            ada_price = float(ticker['price'])
            
            # Calcular balance total en USDT
            total_balance = usdt_balance + (ada_balance * ada_price)
            
            logger.info(f"💰 Balance inicial calculado desde Binance:")
            logger.info(f"   USDT: ${usdt_balance:.2f}")
            logger.info(f"   ADA: {ada_balance:.2f} (${ada_balance * ada_price:.2f})")
            logger.info(f"   Total: ${total_balance:.2f}")
            
            return total_balance
            
        except Exception as e:
            logger.error(f"❌ Error calculando balance desde Binance: {e}")
            logger.warning("⚠️ Usando balance por defecto: $10.00")
            return 10.0
    
    def load_history(self):
        """Carga el historial de posiciones desde archivo"""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.position_history = data.get('history', [])
                    # Solo cargar balance si no hay historial
                    if not self.position_history:
                        self.initial_balance = data.get('initial_balance', self.initial_balance)
                        self.current_balance = data.get('current_balance', self.current_balance)
                        self.total_pnl = data.get('total_pnl', 0.0)
                logger.info(f"📂 Historial cargado: {len(self.position_history)} posiciones")
            else:
                logger.info("📂 No se encontró archivo de historial, iniciando desde cero")
        except Exception as e:
            logger.error(f"❌ Error cargando historial: {e}")
            self.position_history = []
    
    def save_history(self):
        """Guarda el historial de posiciones en archivo"""
        try:
            # Crear backup del archivo anterior
            if os.path.exists(HISTORY_FILE):
                import shutil
                shutil.copy2(HISTORY_FILE, BACKUP_FILE)
            
            data = {
                'history': self.position_history,
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_pnl': self.total_pnl,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"💾 Historial guardado: {len(self.position_history)} posiciones")
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
                'type': signal,
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
                if position['type'] == 'BUY':
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
                
                # Agregar al historial
                self.position_history.append({
                    'bot_type': bot_type,
                    'position_id': position_id,
                    **position
                })
                
                # Actualizar saldo de cuenta
                self.update_balance(position['pnl_net'])
                
                # Remover posición activa
                del self.positions[bot_type][position_id]
        
        # Si tenemos posiciones abiertas, actualizar precios y PnL
        if self.positions[bot_type]:
            for position_id, position in self.positions[bot_type].items():
                position['current_price'] = current_price
                
                # Calcular PnL bruto actual
                if position['type'] == 'BUY':
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
        
        # Guardar historial periódicamente
        if len(self.position_history) % 10 == 0:  # Cada 10 posiciones
            self.save_history()
    
    def update_balance(self, pnl_net: float):
        """Actualiza el balance de la cuenta"""
        self.total_pnl += pnl_net
        self.current_balance = self.initial_balance + self.total_pnl
        
        logger.info(f"💰 Saldo actualizado: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.2f})")
    
    def get_account_balance(self) -> Dict[str, Any]:
        """Obtiene información del saldo de la cuenta"""
        balance_change_pct = ((self.current_balance - self.initial_balance) / self.initial_balance) * 100
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'total_pnl': self.total_pnl,
            'balance_change_pct': balance_change_pct,
            'is_profitable': self.current_balance > self.initial_balance
        }
    
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
