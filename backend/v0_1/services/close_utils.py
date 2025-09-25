#!/usr/bin/env python3
"""
Utilities to close synthetic positions consistently across reconciler and endpoints.
"""

from datetime import datetime
from typing import Dict, Any, Optional


def close_synth_position(
    *,
    trading_tracker,
    real_trading_manager,
    bot_registry,
    bot_type: str,
    position_id: str,
    current_price: Optional[float] = None,
    reason: str = "Manual",
) -> Dict[str, Any]:
    """Close a synthetic position and persist all side-effects.

    - Updates history via trading_tracker.close_order
    - Adjusts synthetic balances via trading_tracker.adjust_synth_balances
    - Marks position as closed in active_positions and persists snapshot
    Returns a dict with pnl, exit_price, and identifiers.
    """

    # Resolve price
    if current_price is None:
        try:
            current_price = real_trading_manager.get_current_price("DOGEUSDT")
        except Exception:
            current_price = None
    if not current_price:
        raise ValueError("No current price available to close position")

    # Fetch active position from memory or snapshot
    pos = None
    try:
        pos = (trading_tracker.active_positions.get(bot_type, {}) or {}).get(
            position_id
        )
    except Exception:
        pos = None
    if pos is None and hasattr(trading_tracker, "persistence"):
        try:
            snap = trading_tracker.persistence.get_active_positions() or {}
            pos = (snap.get(bot_type, {}) or {}).get(position_id)
        except Exception:
            pos = None

    if pos is None:
        # Final fallback: try to scan bot synthetic list
        try:
            bot = bot_registry.get_all_bots().get(bot_type)
            if bot and getattr(bot, "synthetic_positions", None):
                for p in bot.synthetic_positions:
                    pid = str(p.get("id") or p.get("position_id"))
                    if pid == position_id:
                        pos = p
                        break
        except Exception:
            pass

    if pos is None:
        raise ValueError("Position not found")

    # Normalize fields
    side = str(pos.get("signal_type") or pos.get("type") or "BUY").upper()
    entry_price = float(pos.get("entry_price") or pos.get("entry") or 0)
    qty = float(pos.get("quantity") or pos.get("qty") or 0)
    order_id = str(
        pos.get("order_id") or pos.get("id") or pos.get("position_id") or position_id
    )

    # Fees
    fee_rate = float(getattr(trading_tracker, "fee_rate", 0.001))
    exit_fee = float(current_price) * qty * fee_rate

    # Persist in history
    if hasattr(trading_tracker, "close_order"):
        trading_tracker.close_order(
            order_id=order_id,
            close_price=float(current_price),
            fees_paid=exit_fee,
            reason=reason,
        )

    # Adjust synthetic balances
    if hasattr(trading_tracker, "adjust_synth_balances"):
        # Ejecutar y no silenciar errores: es crítico para liberar locks y ajustar saldos
        trading_tracker.adjust_synth_balances(
            side=side,
            action="close",
            price=float(current_price),
            quantity=qty,
            fee=exit_fee,
        )

    # Mark as closed in active_positions and persist
    if bot_type not in trading_tracker.active_positions:
        trading_tracker.active_positions[bot_type] = {}
    closed = dict(pos)
    closed.update(
        {
            "status": "closed",
            "is_closed": True,
            "close_reason": reason,
            "close_price": float(current_price),
            "close_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    trading_tracker.active_positions[bot_type][position_id] = closed
    trading_tracker.persistence.set_active_positions(trading_tracker.active_positions)

    pnl_gross = (
        (float(current_price) - entry_price) * qty
        if side == "BUY"
        else (entry_price - float(current_price)) * qty
    )
    pnl_net = pnl_gross - exit_fee

    return {
        "bot_type": bot_type,
        "position_id": position_id,
        "order_id": order_id,
        "exit_price": float(current_price),
        "pnl": pnl_net,
    }
