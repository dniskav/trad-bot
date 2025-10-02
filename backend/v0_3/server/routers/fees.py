#!/usr/bin/env python3
"""
Fees Router
Returns maker/taker fees for a given symbol (cached)
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import time
import aiohttp
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "shared"))

from shared.settings import env_str
from shared.logger import get_logger

log = get_logger("fees.router")
router = APIRouter(prefix="/fees", tags=["fees"])

_cache: Dict[str, Dict] = {}
_ttl_seconds = 60 * 30  # 30 min


async def _fetch_spot_trade_fee(sym: str) -> Dict:
    api_base = env_str("BINANCE_API_BASE", "https://api.binance.com")
    api_key = env_str("BINANCE_API_KEY", "")
    url = f"{api_base}/sapi/v1/asset/tradeFee?symbol={sym}"
    headers = {"X-MBX-APIKEY": api_key} if api_key else {}
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as sess:
        async with sess.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=resp.status, detail=await resp.text())
            data = await resp.json()
            # Response can be list or object depending on API version
            item = data[0] if isinstance(data, list) else data
            maker = abs(
                float(
                    item.get("makerCommission", item.get("makerCommissionRate", 0.001))
                )
            )
            taker = abs(
                float(
                    item.get("takerCommission", item.get("takerCommissionRate", 0.001))
                )
            )
            return {
                "symbol": sym,
                "maker": maker,
                "taker": taker,
                "source": "binance_spot",
            }


@router.get("/{symbol}")
async def get_fees(symbol: str):
    """Return maker/taker fees for a symbol.
    Tries Binance first (if API key available), falls back to defaults.
    Caches the result for a short TTL.
    """
    sym = symbol.upper()
    now = time.time()
    entry = _cache.get(sym)
    if entry and (now - entry.get("_ts", 0)) < _ttl_seconds:
        return {k: v for k, v in entry.items() if k != "_ts"}

    # Try Binance Spot trade fee endpoint
    try:
        fees = await _fetch_spot_trade_fee(sym)
        fees_ret = fees
    except Exception as e:
        log.warning(f"fees: fallback for {sym}: {e}")
        fees_ret = {
            "symbol": sym,
            "maker": 0.0010,
            "taker": 0.0010,
            "source": "default",
        }

    fees_ret_with_ts = {**fees_ret, "_ts": now}
    _cache[sym] = fees_ret_with_ts
    return fees_ret
