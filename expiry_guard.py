# -*- coding: utf-8 -*-
"""
expiry_guard.py
Флагует снапшоты, попавшие в окно вокруг дневной экспирации (11:00 MSK / 08:00 UTC),
где сигналы по OI часто зашумлены роллом контрактов.
"""

from datetime import datetime, timedelta

EXPIRY_HOUR_MSK = 11
EXPIRY_MINUTE_MSK = 0
GUARD_WINDOW_MIN = 45  # окно до и после экспирации


def check_expiry_guard(ts_iso: str):
    if not ts_iso:
        return {"flagged": False, "reason": "нет метки времени в отчёте"}

    try:
        dt = datetime.fromisoformat(ts_iso)
    except ValueError:
        return {"flagged": False, "reason": "не удалось разобрать время"}

    expiry_today = dt.replace(hour=EXPIRY_HOUR_MSK, minute=EXPIRY_MINUTE_MSK, second=0, microsecond=0)
    candidates = [expiry_today, expiry_today - timedelta(days=1), expiry_today + timedelta(days=1)]
    nearest = min(candidates, key=lambda e: abs((dt - e).total_seconds()))
    diff_min = abs((dt - nearest).total_seconds()) / 60

    if diff_min <= GUARD_WINDOW_MIN:
        return {
            "flagged": True,
            "reason": f"снапшот в пределах {int(diff_min)} мин от экспирации 11:00 МСК — сигнал может быть зашумлён",
        }
    return {"flagged": False, "reason": None}
