#!/usr/bin/env python3
"""
Order management endpoints
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# These will be injected by the main server
trading_tracker = None

def set_dependencies(tt):
    """Set dependencies from main server"""
    global trading_tracker
    trading_tracker = tt

@router.get("/orders/status")
async def get_orders_status():
    """Obtiene el estado detallado de todas las órdenes"""
    try:
        if not trading_tracker:
            return JSONResponse({"error": "Trading tracker no inicializado"}, status_code=500)
        
        open_orders = trading_tracker.get_open_orders()
        closed_orders = trading_tracker.get_closed_orders()
        
        # Formatear órdenes para el frontend
        def format_order(order):
            return {
                'order_id': order['order_id'],
                'position_id': order['position_id'],
                'bot_type': order['bot_type'],
                'symbol': order['symbol'],
                'side': order['side'],
                'quantity': order['quantity'],
                'entry_price': order['entry_price'],
                'entry_time': order['entry_time'].isoformat() if order['entry_time'] else None,
                'status': order['status'],
                'current_price': order['current_price'],
                'pnl': order['pnl'],
                'pnl_percentage': order['pnl_percentage'],
                'close_price': order['close_price'],
                'close_time': order['close_time'].isoformat() if order['close_time'] else None,
                'duration_minutes': order['duration_minutes'],
                'fees_paid': order['fees_paid'],
                'net_pnl': order['net_pnl']
            }
        
        return JSONResponse({
            'open_orders': [format_order(order) for order in open_orders],
            'closed_orders': [format_order(order) for order in closed_orders[-10:]],  # Últimas 10 cerradas
            'summary': {
                'total_open': len(open_orders),
                'total_closed': len(closed_orders),
                'total_trades': len(open_orders) + len(closed_orders)
            }
        })
    except Exception as e:
        logger.error(f"Error getting orders status: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
