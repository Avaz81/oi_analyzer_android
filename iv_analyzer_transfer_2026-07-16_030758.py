# -*- coding: utf-8 -*-
"""
iv_analyzer.py
IV Rank / IV Percentile с двухуровневым адаптивным окном (короткое/длинное)
и накопительным периодом, как в oi_monitor.
"""

SHORT_WINDOW = 10   # снапшотов
LONG_WINDOW = 30     # снапшотов
MIN_FOR_FULL_VERDICT = 10


def _rank_and_percentile(current, history):
    if not history:
        return None, None
    lo, hi = min(history), max(history)
    rank = 50.0 if hi == lo else (current - lo) / (hi - lo) * 100
    below = sum(1 for v in history if v <= current)
    percentile = below / len(history) * 100
    return round(rank, 1), round(percentile, 1)


def _zone(percentile):
    if percentile is None:
        return "⚪", "недостаточно данных"
    if percentile < 20:
        return "🟢", "IV дёшева — благоприятно для покупки опционов"
    if percentile < 40:
        return "🟡", "IV ниже среднего — приемлемо для покупки"
    if percentile < 70:
        return "🟠", "IV выше среднего — риск IV crush повышен"
    return "🔴", "IV дорогая — покупка опционов невыгодна"


def analyze_iv(current_iv, history_short_first: list):
    """
    history_short_first: список atm_iv, начиная с самого свежего (id DESC),
    как возвращает storage.get_iv_history().
    """
    if current_iv is None:
        return {
            "available": False,
            "verdict": "IV не найдена в отчёте",
        }

    n = len(history_short_first)
    short_hist = history_short_first[:SHORT_WINDOW]
    long_hist = history_short_first[:LONG_WINDOW]

    rank_s, pct_s = _rank_and_percentile(current_iv, short_hist)
    rank_l, pct_l = _rank_and_percentile(current_iv, long_hist)

    full_verdict = n >= MIN_FOR_FULL_VERDICT
    # используем длинное окно если данных хватает, иначе короткое
    pct_used = pct_l if (full_verdict and len(long_hist) >= MIN_FOR_FULL_VERDICT) else pct_s
    zone_icon, zone_text = _zone(pct_used if full_verdict else None)

    return {
        "available": True,
        "current_iv": current_iv,
        "history_points": n,
        "rank_short": rank_s,
        "percentile_short": pct_s,
        "rank_long": rank_l,
        "percentile_long": pct_l,
        "full_verdict": full_verdict,
        "zone_icon": zone_icon,
        "zone_text": zone_text,
        "percentile_used": pct_used,
    }
