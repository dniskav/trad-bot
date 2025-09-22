#!/usr/bin/env python3
"""
Position service - business logic for position management
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# These will be injected by the main server
real_trading_manager = None
trading_tracker = None
bot_registry = None

def set_dependencies(rtm, tt, br):
    """Set dependencies from main server"""
    global real_trading_manager, trading_tracker, bot_registry
    real_trading_manager = rtm
    trading_tracker = tt
    bot_registry = br

def get_position_info_for_frontend(current_price=None):
    """
    Obtiene información de posiciones del RealTradingManager y bots plug-and-play, formateada para el frontend
    """
    # Obtener posiciones del RealTradingManager
    real_positions = real_trading_manager.active_positions
    
    # Obtener datos del TradingTracker para historial y estadísticas
    tracker_data = trading_tracker.get_all_positions()
    
    # Formatear posiciones para el frontend - formato compatible con ActivePositions
    formatted_positions = {}
    
    # Procesar bots legacy (conservative, aggressive)
    for bot_type in ['conservative', 'aggressive']:
        bot_positions = real_positions.get(bot_type, {})
        
        if not bot_positions:
            # No hay posiciones activas
            formatted_positions[bot_type] = {}
        else:
            # Formatear cada posición individualmente
            formatted_bot_positions = {}
            for position_id, position in bot_positions.items():
                entry_price = position['entry_price']
                quantity = position['quantity']
                
                # Calcular PnL si tenemos precio actual
                pnl = 0.0
                pnl_pct = 0.0
                if current_price and entry_price > 0:
                    if position['side'] == 'BUY':
                        pnl = (current_price - entry_price) * quantity
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:  # SELL
                        pnl = (entry_price - current_price) * quantity
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                
                formatted_bot_positions[position_id] = {
                    'id': position_id,
                    'bot_type': bot_type,
                    'type': position['side'],
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'entry_time': position['entry_time'],
                    'current_price': current_price or entry_price,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'pnl_net': pnl,
                    'pnl_net_pct': pnl_pct,
                    'timestamp': position['entry_time'],
                    'is_synthetic': False,  # Flag para posiciones reales
                    'is_plugin_bot': False,  # Flag para bots legacy
                    'bot_on': real_trading_manager.is_bot_active(bot_type)
                }
            
            formatted_positions[bot_type] = formatted_bot_positions
    
    # Procesar bots plug-and-play (posiciones sintéticas)
    all_bots = bot_registry.get_all_bots()
    for bot_name, bot in all_bots.items():
        # Saltar bots legacy
        if bot_name in ['conservative', 'aggressive']:
            continue
            
        # Mostrar posiciones sintéticas aunque el bot esté apagado
        if bot.config.synthetic_mode and bot.synthetic_positions:
            formatted_bot_positions = {}
            
            for position in bot.synthetic_positions:
                if position['status'] == 'open':
                    entry_price = position['entry_price']
                    quantity = position['quantity']
                    position_id = position['id']
                    
                    # Calcular PnL si tenemos precio actual
                    pnl = 0.0
                    pnl_pct = 0.0
                    if current_price and entry_price > 0:
                        if position['signal_type'] == 'BUY':
                            pnl = (current_price - entry_price) * quantity
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        else:  # SELL
                            pnl = (entry_price - current_price) * quantity
                            pnl_pct = ((entry_price - current_price) / entry_price) * 100
                    
                    formatted_bot_positions[position_id] = {
                        'id': position_id,
                        'bot_type': bot_name,
                        'type': position['signal_type'],
                        'entry_price': entry_price,
                        'quantity': quantity,
                        'entry_time': position['timestamp'],
                        'current_price': current_price or entry_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'pnl_net': pnl,
                        'pnl_net_pct': pnl_pct,
                        'timestamp': position['timestamp'],
                        'is_synthetic': True,  # Flag para posiciones sintéticas
                        'is_plugin_bot': True,  # Flag para bots plug-and-play
                        'bot_on': bot.is_active,
                        'stop_loss': position.get('stop_loss'),
                        'take_profit': position.get('take_profit')
                    }
            
            if formatted_bot_positions:
                formatted_positions[bot_name] = formatted_bot_positions
    
    # Convertir historial de órdenes al formato esperado por el frontend
    formatted_history = []
    if tracker_data.get('history'):
        for order_record in tracker_data['history']:
            formatted_history.append(format_order_for_frontend(order_record))
    
    return {
        'active_positions': formatted_positions,
        'history': formatted_history,
        'statistics': tracker_data.get('statistics', {}),
        'account_balance': tracker_data.get('account_balance', {}),
        'margin_info': real_trading_manager.get_margin_level() if real_trading_manager.leverage > 1 else None
    }

def format_order_for_frontend(order_record):
    """Formatea un registro de orden para el frontend"""
    status = order_record.get('status', 'UNKNOWN')
    
    return {
        'id': order_record.get('order_id', ''),
        'bot_type': order_record.get('bot_type', ''),
        'type': order_record.get('side', ''),
        'entry_price': order_record.get('entry_price', 0),
        'quantity': order_record.get('quantity', 0),
        'entry_time': order_record.get('entry_time', ''),
        'current_price': order_record.get('current_price', 0),
        'pnl': order_record.get('pnl', 0),
        'pnl_pct': order_record.get('pnl_percentage', 0),
        'pnl_net': order_record.get('net_pnl', 0),
        'pnl_net_pct': order_record.get('pnl_percentage', 0),  # Usar el mismo valor por ahora
        'timestamp': order_record.get('entry_time', ''),
        'close_price': order_record.get('close_price'),
        'close_time': order_record.get('close_time'),
        'duration_minutes': order_record.get('duration_minutes', 0),
        'fees_paid': order_record.get('fees_paid', 0),
        'status': status,
        'is_closed': status not in ['OPEN', 'UPDATED'],  # Campo para identificar si está cerrada
        'duration_minutes': order_record.get('duration_minutes', 0),
        'is_synthetic': order_record.get('is_synthetic', False),  # Flag para posiciones sintéticas
        'is_plugin_bot': order_record.get('is_plugin_bot', False)  # Flag para bots plug-and-play
    }
