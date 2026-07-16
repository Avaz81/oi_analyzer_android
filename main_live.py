#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_live.py — автономный режим: сам тянет данные с Deribit и Bybit,
без ручной вставки отчёта. Требует интернет и пакет requests:

    pip install requests --break-system-packages

Запуск разово:
    python3 main_live.py

Запуск в цикле (например каждые 15 минут):
    python3 main_live.py --loop 900
"""

import sys
import time

from live_report_builder import build_live_snapshot
from iv_analyzer import analyze_iv
from wall_analyzer import detect_wall_melt, detect_confluence
from expiry_guard import check_expiry_guard
from signal_engine import build_verdict
import storage
from main import format_output  # переиспользуем готовый форматтер вывода


def run_once():
    try:
        parsed = build_live_snapshot()
    except Exception as e:
        print(f"❌ Не удалось получить данные: {e}")
        return

    previous_list = storage.get_last(1)
    previous = previous_list[0] if previous_list else None

    iv_history = storage.get_iv_history(limit=30)
    iv_result = analyze_iv(parsed.get("atm_iv"), iv_history)

    melt_result = detect_wall_melt(parsed, previous)
    confluence = detect_confluence(parsed)
    expiry_result = check_expiry_guard(parsed.get("ts_iso"))
    verdict = build_verdict(parsed, iv_result, melt_result, confluence, expiry_result)

    print("\n" + format_output(parsed, iv_result, melt_result, confluence, expiry_result, verdict))

    storage.save_snapshot(parsed)
    print(f"\n(снапшот сохранён, всего в истории: {storage.count_snapshots()})")


def main():
    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 900
        print(f"Автономный режим: обновление каждые {interval} сек. Ctrl+C для остановки.")
        while True:
            run_once()
            time.sleep(interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
