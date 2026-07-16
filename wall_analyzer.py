# -*- coding: utf-8 -*-
"""
wall_analyzer.py
Детекция таяния/укрепления OI-стен (сравнение с прошлым снапшотом)
и confluence со уровнями Volume Profile (POC/VAH/VAL/VWAP).
"""

MELT_THRESHOLD_PCT = 15.0     # изменение OI на страйке, чтобы считать "тает"/"растёт"
CONFLUENCE_TOLERANCE_PCT = 1.0  # насколько близко страйк должен быть к уровню


def detect_wall_melt(current: dict, previous: dict):
    result = {"call_wall": None, "put_wall": None}

    if previous is None:
        return result

    def _change(cur_strike, cur_val, prev_strike, prev_val):
        if cur_val is None or prev_val is None or prev_val == 0:
            return None
        if cur_strike != prev_strike:
            # стена сместилась на новый страйк — считаем это отдельным сигналом
            return {"status": "moved", "from": prev_strike, "to": cur_strike}
        pct = (cur_val - prev_val) / prev_val * 100
        if pct <= -MELT_THRESHOLD_PCT:
            status = "melting"   # ⚠ стена тает — риск пробоя
        elif pct >= MELT_THRESHOLD_PCT:
            status = "building"  # стена укрепляется — выше шанс отбоя
        else:
            status = "stable"
        return {"status": status, "change_pct": round(pct, 1)}

    result["call_wall"] = _change(
        current.get("max_call_oi_strike"), current.get("max_call_oi_value"),
        previous.get("max_call_oi_strike"), previous.get("max_call_oi_value"),
    )
    result["put_wall"] = _change(
        current.get("max_put_oi_strike"), current.get("max_put_oi_value"),
        previous.get("max_put_oi_strike"), previous.get("max_put_oi_value"),
    )
    return result


def detect_confluence(current: dict):
    """Проверяет, совпадают ли стены OI с ключевыми уровнями Volume Profile/VWAP."""
    anchors = {
        "POC": current.get("poc"),
        "VWAP": current.get("vwap"),
        "VAH": current.get("vah"),
        "VAL": current.get("val"),
    }
    matches = []
    for wall_name, strike in (
        ("Call wall", current.get("max_call_oi_strike")),
        ("Put wall", current.get("max_put_oi_strike")),
    ):
        if not strike:
            continue
        for anchor_name, anchor_val in anchors.items():
            if not anchor_val:
                continue
            dist_pct = abs(strike - anchor_val) / anchor_val * 100
            if dist_pct <= CONFLUENCE_TOLERANCE_PCT:
                matches.append(f"{wall_name} ≈ {anchor_name} ({dist_pct:.2f}%)")
    return matches
