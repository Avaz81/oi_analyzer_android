# -*- coding: utf-8 -*-
"""
live_bybit.py
Тянет 15-минутные свечи BTCUSDT с публичного Bybit API (без ключей)
и считает: заякоренный VWAP (с 08:00 UTC текущих суток) и
3-дневный Volume Profile (POC, VAH, VAL).
"""

import time
import requests
from datetime import datetime, timezone, timedelta

BASE = "https://api.bybit.com/v5/market/kline"
SYMBOL = "BTCUSDT"
INTERVAL = "15"  # минут


def _fetch_klines(start_ms, end_ms):
    candles = []
    cursor_end = end_ms
    for _ in range(5):  # защита от бесконечного цикла, максимум 5 запросов по 1000 свечей
        params = {
            "category": "linear",
            "symbol": SYMBOL,
            "interval": INTERVAL,
            "start": start_ms,
            "end": cursor_end,
            "limit": 1000,
        }
        r = requests.get(BASE, params=params, timeout=15)
        r.raise_for_status()
        rows = r.json()["result"]["list"]  # [start, open, high, low, close, volume, turnover]
        if not rows:
            break
        candles.extend(rows)
        oldest_ts = int(rows[-1][0])
        if oldest_ts <= start_ms:
            break
        cursor_end = oldest_ts - 1
    return candles


def _to_float_rows(rows):
    out = []
    for r in rows:
        out.append({
            "ts": int(r[0]),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        })
    return out


def get_anchored_vwap():
    now = datetime.now(timezone.utc)
    anchor = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now < anchor:
        anchor -= timedelta(days=1)
    start_ms = int(anchor.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    rows = _to_float_rows(_fetch_klines(start_ms, end_ms))
    if not rows:
        return None

    num, den = 0.0, 0.0
    for c in rows:
        typical = (c["high"] + c["low"] + c["close"]) / 3
        num += typical * c["volume"]
        den += c["volume"]
    return round(num / den, 1) if den else None


def get_volume_profile(days=3, bin_size=50):
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)

    rows = _to_float_rows(_fetch_klines(start_ms, end_ms))
    if not rows:
        return None, None, None

    buckets = {}
    for c in rows:
        typical = (c["high"] + c["low"] + c["close"]) / 3
        bucket = round(typical / bin_size) * bin_size
        buckets[bucket] = buckets.get(bucket, 0) + c["volume"]

    if not buckets:
        return None, None, None

    total_vol = sum(buckets.values())
    poc = max(buckets, key=buckets.get)

    # расширяем от POC пока не наберём 70% объёма (Value Area)
    sorted_prices = sorted(buckets.keys())
    poc_idx = sorted_prices.index(poc)
    covered = buckets[poc]
    lo_idx, hi_idx = poc_idx, poc_idx
    target = total_vol * 0.7

    while covered < target and (lo_idx > 0 or hi_idx < len(sorted_prices) - 1):
        lo_val = buckets[sorted_prices[lo_idx - 1]] if lo_idx > 0 else -1
        hi_val = buckets[sorted_prices[hi_idx + 1]] if hi_idx < len(sorted_prices) - 1 else -1
        if hi_val >= lo_val:
            hi_idx += 1
            covered += buckets[sorted_prices[hi_idx]]
        else:
            lo_idx -= 1
            covered += buckets[sorted_prices[lo_idx]]

    val = sorted_prices[lo_idx]
    vah = sorted_prices[hi_idx]
    return round(poc, 1), round(val, 1), round(vah, 1)
