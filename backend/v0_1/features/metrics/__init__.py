import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api import metrics as _api_metrics  # type: ignore

router = _api_metrics.router

def set_dependencies(real_trading_manager, trading_tracker):
    _api_metrics.set_dependencies(real_trading_manager, trading_tracker)


