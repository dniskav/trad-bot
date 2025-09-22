import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import bots as _api_bots  # type: ignore

router = _api_bots.router

def set_dependencies(real_trading_manager, trading_tracker):
    _api_bots.set_dependencies(real_trading_manager, trading_tracker)


