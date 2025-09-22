import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import klines as _api_klines  # type: ignore

router = _api_klines.router

def set_dependencies(real_trading_manager):
    _api_klines.set_dependencies(real_trading_manager)


