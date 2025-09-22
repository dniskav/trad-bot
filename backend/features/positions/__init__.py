"""
Feature slice: positions
Re-exports router and dependency wiring from existing api/services without
modifying original modules (ports & adapters friendly).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import positions as _api_positions  # type: ignore

# Public router for FastAPI include_router
router = _api_positions.router


def set_dependencies(real_trading_manager, trading_tracker, bot_registry):
    """Proxy to original module's dependency injector."""
    _api_positions.set_dependencies(real_trading_manager, trading_tracker, bot_registry)


