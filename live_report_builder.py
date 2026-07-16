# -*- coding: utf-8 -*-
"""
live_report_builder.py
Собирает данные live_deribit + live_bybit в тот же словарь-схему,
что и report_parser.parse_report(), чтобы использовать те же модули
анализа (iv_analyzer, wall_analyzer, expiry_guard, signal_engine)
без ручной вставки текста.
"""

from datetime import datetime, timezone

import live_deribit
import live_bybit
import storage


def _checklist(price, vwap, poc, val, vah, pcr, call_oi_delta, put_oi_delta):
    checks = []
    checks.append(price is not None and vwap is not None and price > vwap)
    checks.append(price is not None and poc is not None and price > poc)
    checks.append(val is not None and vah is not None and price is not None and val <= price <= vah)
    if pcr is not None and call_oi_delta is not None:
        checks.append(pcr < 2.0)  # эвристика: PCR не в зоне выраженного доминирования путов
    if call_oi_delta is not None:
        checks.append(call_oi_delta >= 0)
    if put_oi_delta is not None:
        checks.append(put_oi_delta <= 0)
    total = len(checks)
    passed = sum(1 for c in checks if c)
    return passed, total


def build_live_snapshot():
    opts = live_deribit.build_options_metrics()
    vwap = live_bybit.get_anchored_vwap()
    poc, val, vah = live_bybit.get_volume_profile()

    price = opts["price"]

    prev_list = storage.get_last(1)
    prev = prev_list[0] if prev_list else None
    call_oi_delta = (opts["max_call_oi_value"] - prev["max_call_oi_value"]) \
        if prev and prev.get("max_call_oi_value") is not None and opts["max_call_oi_value"] is not None else None
    put_oi_delta = (opts["max_put_oi_value"] - prev["max_put_oi_value"]) \
        if prev and prev.get("max_put_oi_value") is not None and opts["max_put_oi_value"] is not None else None

    passed, total = _checklist(price, vwap, poc, val, vah, opts["pcr"], call_oi_delta, put_oi_delta)
    conviction_score = round(passed / total * 100) if total else None

    up_pct = None
    down_pct = None
    if total:
        ratio = passed / total
        up_pct = max(20, min(80, round(50 + (ratio - 0.5) * 60)))
        down_pct = 100 - up_pct

    if conviction_score is None:
        bias = "Neutral"
    elif conviction_score >= 65:
        bias = "Bullish"
    elif conviction_score <= 35:
        bias = "Bearish"
    else:
        bias = "Neutral"

    now = datetime.now(timezone.utc).astimezone()
    next_num = storage.count_snapshots() + 1

    parsed = {
        "snapshot_num": next_num,
        "ts_raw": now.strftime("%d.%m.%Y %H:%M"),
        "ts_iso": now.isoformat(),
        "price": price,
        "vwap": vwap,
        "poc": poc,
        "val": val,
        "vah": vah,
        "pcr": opts["pcr"],
        "atm_iv": opts["atm_iv"],
        "above_call": opts["above_call"],
        "at_call": opts["at_call"],
        "at_put": opts["at_put"],
        "below_put": opts["below_put"],
        "max_call_oi_strike": opts["max_call_oi_strike"],
        "max_call_oi_value": opts["max_call_oi_value"],
        "max_put_oi_strike": opts["max_put_oi_strike"],
        "max_put_oi_value": opts["max_put_oi_value"],
        "conviction_score": conviction_score,
        "oi_confidence_stars": round((passed / total) * 5) if total else None,
        "market_bias": bias,
        "checklist_pass": passed,
        "checklist_total": total,
        "scenario_up_pct": up_pct,
        "scenario_down_pct": down_pct,
        "support_levels": [],
        "resistance_levels": [],
        "raw_text": f"[live snapshot, ближайшая экспирация опционов: {opts['expiry_iso']}]",
    }
    return parsed
