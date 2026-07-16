# -*- coding: utf-8 -*-
"""
live_deribit.py
Тянет данные по опционам BTC напрямую с публичного API Deribit
(без ключей, без авторизации). Берёт ближайшую по дате экспирацию
(что соответствует твоим ~24h DTE контрактам).
"""

import re
import requests
from datetime import datetime, timezone

BASE = "https://www.deribit.com/api/v2/public"


def _get(path, params):
    r = requests.get(f"{BASE}/{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()["result"]


def _parse_instrument(name):
    # формат: BTC-17JUL26-65000-C
    m = re.match(r"BTC-(\d{1,2}[A-Z]{3}\d{2})-(\d+)-([CP])", name)
    if not m:
        return None
    try:
        expiry = datetime.strptime(m.group(1), "%d%b%y").replace(
            hour=8, minute=0, tzinfo=timezone.utc  # деривативы экспирируются в 08:00 UTC
        )
    except ValueError:
        return None
    return {
        "expiry": expiry,
        "strike": float(m.group(2)),
        "type": m.group(3),  # C или P
    }


def get_index_price():
    res = _get("get_index_price", {"index_name": "btc_usd"})
    return float(res["index_price"])


def get_nearest_expiry_snapshot():
    """Возвращает сырой список инструментов ближайшей экспирации + текущую цену."""
    price = get_index_price()
    all_instruments = _get(
        "get_book_summary_by_currency", {"currency": "BTC", "kind": "option"}
    )

    parsed = []
    for inst in all_instruments:
        info = _parse_instrument(inst["instrument_name"])
        if not info:
            continue
        info["open_interest"] = inst.get("open_interest") or 0
        info["mark_iv"] = inst.get("mark_iv")  # уже в % (например 55.2)
        parsed.append(info)

    if not parsed:
        raise RuntimeError("Deribit не вернул инструменты опционов BTC")

    now = datetime.now(timezone.utc)
    future = [p for p in parsed if p["expiry"] > now]
    nearest_expiry = min((p["expiry"] for p in future), default=min(p["expiry"] for p in parsed))
    nearest = [p for p in parsed if p["expiry"] == nearest_expiry]

    return price, nearest_expiry, nearest


def build_options_metrics():
    """Считает ATM IV, PCR, OI-стены, распределение OI выше/на/ниже цены."""
    price, expiry, instruments = get_nearest_expiry_snapshot()

    calls = [i for i in instruments if i["type"] == "C"]
    puts = [i for i in instruments if i["type"] == "P"]

    call_oi_total = sum(i["open_interest"] for i in calls)
    put_oi_total = sum(i["open_interest"] for i in puts)
    pcr = round(put_oi_total / call_oi_total, 3) if call_oi_total else None

    # ATM IV: средняя IV колла и пута на ближайшем к цене страйке
    def _closest(items):
        return min(items, key=lambda i: abs(i["strike"] - price)) if items else None

    atm_call = _closest(calls)
    atm_put = _closest(puts)
    ivs = [i["mark_iv"] for i in (atm_call, atm_put) if i and i.get("mark_iv")]
    atm_iv = round(sum(ivs) / len(ivs), 2) if ivs else None

    def _max_oi(items):
        if not items:
            return None, None
        best = max(items, key=lambda i: i["open_interest"])
        return best["strike"], int(best["open_interest"])

    max_call_strike, max_call_val = _max_oi(calls)
    max_put_strike, max_put_val = _max_oi(puts)

    band = price * 0.005  # +-0.5% считаем "на цене"
    above_call = sum(i["open_interest"] for i in calls if i["strike"] > price + band)
    at_call = sum(i["open_interest"] for i in calls if abs(i["strike"] - price) <= band)
    at_put = sum(i["open_interest"] for i in puts if abs(i["strike"] - price) <= band)
    below_put = sum(i["open_interest"] for i in puts if i["strike"] < price - band)

    return {
        "price": round(price, 1),
        "expiry_iso": expiry.isoformat(),
        "atm_iv": atm_iv,
        "pcr": pcr,
        "above_call": int(above_call),
        "at_call": int(at_call),
        "at_put": int(at_put),
        "below_put": int(below_put),
        "max_call_oi_strike": max_call_strike,
        "max_call_oi_value": max_call_val,
        "max_put_oi_strike": max_put_strike,
        "max_put_oi_value": max_put_val,
    }
