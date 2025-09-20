#!/usr/bin/env python3
"""
Sistema de tracking de posiciones para el trading bot
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
    """Rastrea las posiciones de trading en tiempo real"""
    
    def __init__(self):
        self.positions = {
            'conservative': None,
            'aggressive': None
        }
        self.last_signals = {
            'conservative': 'HOLD',
            'aggressive': 'HOLD'
        }
        # Historial de posiciones cerradas
        self.position_history = []
        # Sistema de saldo de cuenta
        self.initial_balance = 1000.0  # Saldo inicial en USDT
        self.current_balance = 1000.0   # Saldo actual
        self.total_pnl = 0.0           # PnL total acumulado
        
        # Cargar datos existentes al inicio
        self.load_history()
        # Comisiones de Binance (usando BNB para descuento)
        self.fee_rate = 0.00075  # 0.075% por trade con BNB
        self.total_fee_rate = 0.0015  # 0.15% total (compra + venta)
        
        # Stop Loss y Take Profit recomendados por tipo de bot
        self.stop_loss_config = {
            'conservative': {'stop_loss': 0.015, 'take_profit': 0.020},  # 1.5% SL, 2.0% TP
            'aggressive': {'stop_loss': 0.008, 'take_profit': 0.012},   # 0.8% SL, 1.2% TP
            'demo': {'stop_loss': 0.010, 'take_profit': 0.015}           # 1.0% SL, 1.5% TP
        }
    
    def calculate_stop_loss_take_profit(self, bot_type: str, signal: str, entry_price: float):
        """Calcula stop loss y take profit basado en el tipo de bot"""
        config = self.stop_loss_config.get(bot_type, self.stop_loss_config['demo'])
        
        if signal == 'BUY':
            stop_loss = entry_price * (1 - config['stop_loss'])
            take_profit = entry_price * (1 + config['take_profit'])
        else:  # SELL
            stop_loss = entry_price * (1 + config['stop_loss'])
            take_profit = entry_price * (1 - config['take_profit'])
        
        return stop_loss, take_profit
    
    def add_to_history(self, position_data: Dict[str, Any]):
        """Agrega una posición cerrada al historial"""
        # Convertir datetime a string para JSON serialization
        history_entry = position_data.copy()
        if 'entry_time' in history_entry and hasattr(history_entry['entry_time'], 'isoformat'):
            history_entry['entry_time'] = history_entry['entry_time'].isoformat()
        if 'exit_time' in history_entry and hasattr(history_entry['exit_time'], 'isoformat'):
            history_entry['exit_time'] = history_entry['exit_time'].isoformat()
        
        self.position_history.append(history_entry)
        
        # Mantener solo las últimas 100 posiciones para evitar memoria excesiva
        if len(self.position_history) > 100:
            self.position_history = self.position_history[-100:]
        
        # Guardar automáticamente después de cada posición
        self.save_history()
    
    def save_history(self):
        """Guarda el historial en un archivo JSON"""
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            
            # Crear backup del archivo actual si existe
            if os.path.exists(HISTORY_FILE):
                import shutil
                shutil.copy2(HISTORY_FILE, BACKUP_FILE)
            
            # Preparar datos para guardar
            data_to_save = {
                'position_history': self.position_history,
                'initial_balance': self.initial_balance,
                'current_balance': self.current_balance,
                'total_pnl': self.total_pnl,
                'last_signals': self.last_signals,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Guardar en archivo JSON
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Historial guardado: {len(self.position_history)} posiciones en {HISTORY_FILE}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando historial: {e}")
    
    def load_history(self):
        """Carga el historial desde un archivo JSON"""
        try:
            if not os.path.exists(HISTORY_FILE):
                logger.info("📁 No existe archivo de historial, iniciando con datos vacíos")
                return
            
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validar estructura de datos
            if not isinstance(data, dict):
                logger.warning("⚠️ Formato de archivo inválido, iniciando con datos vacíos")
                return
            
            # Cargar datos
            self.position_history = data.get('position_history', [])
            self.initial_balance = data.get('initial_balance', 1000.0)
            self.current_balance = data.get('current_balance', 1000.0)
            self.total_pnl = data.get('total_pnl', 0.0)
            self.last_signals = data.get('last_signals', {
                'conservative': 'HOLD',
                'aggressive': 'HOLD'
            })
            
            # Validar datos cargados
            if not isinstance(self.position_history, list):
                self.position_history = []
            
            logger.info(f"📂 Historial cargado: {len(self.position_history)} posiciones")
            logger.info(f"💰 Saldo cargado: ${self.current_balance:.2f} (PnL: ${self.total_pnl:.2f})")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error de formato JSON: {e}")
            logger.info("🔄 Intentando cargar desde backup...")
            self._load_from_backup()
        except Exception as e:
            logger.error(f"❌ Error cargando historial: {e}")
            logger.info("🔄 Intentando cargar desde backup...")
            self._load_from_backup()
    
    def _load_from_backup(self):
        """Intenta cargar desde archivo de backup"""
        try:
            if not os.path.exists(BACKUP_FILE):
                logger.info("📁 No existe backup, iniciando con datos vacíos")
                return
            
            with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.position_history = data.get('position_history', [])
            self.initial_balance = data.get('initial_balance', 1000.0)
            self.current_balance = data.get('current_balance', 1000.0)
            self.total_pnl = data.get('total_pnl', 0.0)
            self.last_signals = data.get('last_signals', {
                'conservative': 'HOLD',
                'aggressive': 'HOLD'
            })
            
            logger.info(f"🔄 Backup cargado: {len(self.position_history)} posiciones")
            
        except Exception as e:
            logger.error(f"❌ Error cargando backup: {e}")
            logger.info("📁 Iniciando con datos completamente vacíos")
    
    def get_position_history(self, bot_type: str = None, limit: int = 50):
        """Obtiene el historial de posiciones"""
        history = self.position_history
        
        # Filtrar por tipo de bot si se especifica
        if bot_type:
            history = [pos for pos in history if pos.get('bot_type') == bot_type]
        
        # Limitar resultados
        return history[-limit:] if limit else history
    
    def get_bot_statistics(self, bot_type: str = None):
        """Calcula estadísticas de rendimiento"""
        history = self.get_position_history(bot_type)
        
        if not history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_pnl_net': 0,
                'avg_pnl': 0,
                'avg_pnl_net': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        winning_trades = [pos for pos in history if pos.get('pnl_net', 0) > 0]
        losing_trades = [pos for pos in history if pos.get('pnl_net', 0) < 0]
        
        total_pnl = sum(pos.get('pnl', 0) for pos in history)
        total_pnl_net = sum(pos.get('pnl_net', 0) for pos in history)
        
        pnl_values = [pos.get('pnl_net', 0) for pos in history]
        
        return {
            'total_trades': len(history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(history)) * 100 if history else 0,
            'total_pnl': total_pnl,
            'total_pnl_net': total_pnl_net,
            'avg_pnl': total_pnl / len(history) if history else 0,
            'avg_pnl_net': total_pnl_net / len(history) if history else 0,
            'best_trade': max(pnl_values) if pnl_values else 0,
            'worst_trade': min(pnl_values) if pnl_values else 0
        }
    
    def update_balance(self, pnl_net: float):
        """Actualiza el saldo de la cuenta con el PnL neto"""
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
    
    def update_position(self, bot_type: str, signal: str, current_price: float, quantity: float = 1.0):
        """Actualiza la posición de un bot"""
        
        # Si el bot cambió de señal y no tenemos posición abierta
        if (signal in ['BUY', 'SELL'] and 
            self.last_signals[bot_type] == 'HOLD' and 
            self.positions[bot_type] is None):
            
            # Calcular comisión de entrada
            entry_fee = current_price * quantity * self.fee_rate
            
            # Calcular stop loss y take profit
            stop_loss, take_profit = self.calculate_stop_loss_take_profit(bot_type, signal, current_price)
            
            # Abrir nueva posición
            self.positions[bot_type] = {
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
            
            logger.info(f"🚀 {bot_type.upper()} - Nueva posición {signal} a ${current_price:.4f}")
            
        # Si el bot cambió a HOLD y tenemos posición abierta
        elif (signal == 'HOLD' and 
              self.last_signals[bot_type] in ['BUY', 'SELL'] and 
              self.positions[bot_type] is not None):
            
            # Cerrar posición
            position = self.positions[bot_type]
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
            
            # Calcular PnL neto (después de comisiones)
            position['pnl_net'] = position['pnl'] - total_fees
            position['pnl_net_pct'] = (position['pnl_net'] / (position['entry_price'] * position['quantity'])) * 100
            position['total_fees'] = total_fees
            position['bot_type'] = bot_type
            position['close_reason'] = 'Señal Contraria'
            
            logger.info(f"🔒 {bot_type.upper()} - Cerrando posición:")
            logger.info(f"   PnL Bruto: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
            logger.info(f"   Comisiones: ${total_fees:.4f}")
            logger.info(f"   PnL Neto: ${position['pnl_net']:.4f} ({position['pnl_net_pct']:.2f}%)")
            
            # Agregar al historial antes de resetear
            self.add_to_history(position)
            
            # Actualizar saldo de cuenta
            self.update_balance(position['pnl_net'])
            
            # Resetear posición
            self.positions[bot_type] = None
            
        # Si tenemos posición abierta, actualizar precio actual y PnL
        elif self.positions[bot_type] is not None:
            position = self.positions[bot_type]
            position['current_price'] = current_price
            
            # Verificar stop loss y take profit
            should_close = False
            close_reason = ""
            
            if position['type'] == 'BUY':
                if current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
            else:  # SELL
                if current_price >= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price <= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
            
            # Si se debe cerrar por stop loss o take profit
            if should_close:
                # Calcular comisión de salida
                exit_fee = current_price * position['quantity'] * self.fee_rate
                position['exit_fee'] = exit_fee
                total_fees = position['entry_fee'] + exit_fee
                
                # Calcular PnL final
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
                position['exit_time'] = datetime.now()
                position['bot_type'] = bot_type
                position['close_reason'] = close_reason
                
                logger.info(f"🔒 {bot_type.upper()} - Cerrando posición por {close_reason}:")
                logger.info(f"   PnL Bruto: ${position['pnl']:.4f} ({position['pnl_pct']:.2f}%)")
                logger.info(f"   Comisiones: ${total_fees:.4f}")
                logger.info(f"   PnL Neto: ${position['pnl_net']:.4f} ({position['pnl_net_pct']:.2f}%)")
                
                # Agregar al historial antes de resetear
                self.add_to_history(position)
                
                # Actualizar saldo de cuenta
                self.update_balance(position['pnl_net'])
                
                # Resetear posición
                self.positions[bot_type] = None
            else:
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
    
    def get_position_info(self, bot_type: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de la posición actual"""
        return self.positions[bot_type]
    
    def get_all_positions(self) -> Dict[str, Any]:
        """Obtiene información de todas las posiciones"""
        return {
            'conservative': self.positions['conservative'],
            'aggressive': self.positions['aggressive'],
            'last_signals': self.last_signals,
            'history': self.get_position_history(limit=20),
            'statistics': {
                'conservative': self.get_bot_statistics('conservative'),
                'aggressive': self.get_bot_statistics('aggressive'),
                'overall': self.get_bot_statistics()
            },
            'account_balance': self.get_account_balance()
        }

# Instancia global del tracker
trading_tracker = TradingTracker()
