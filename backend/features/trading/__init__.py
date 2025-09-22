import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import trading as _api_trading  # type: ignore

router = _api_trading.router

def set_dependencies(trading_tracker):
    _api_trading.set_dependencies(trading_tracker)


