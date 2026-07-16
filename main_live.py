#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_live.py — автономный режим: сам тянет данные с Deribit и Bybit,
без ручной вставки отчёта. Требует интернет и пакет requests:

    pip install requests --break-system-packages

Запуск разово:
    python3 main_live.py

Запуск в цикле (например каждые 15 минут, строго по часам: :00 :15 :30 :45):
    python3 main_live.py --loop 900

По умолчанию в режиме --loop каждый снапшот целиком отправляется в Telegram
(если настроен secrets.json), а не только алерты по значимым событиям.
Чтобы отключить это и получать в Telegram только алерты — добавь флаг:
    python3 main_live.py --loop 900 --no-tg-snapshots
"""

import sys
import time
from datetime import datetime, timezone

from live_report_builder import build_live_snapshot
from iv_analyzer import analyze_iv
from wall_analyzer import detect_wall_melt, detect_confluence
from expiry_guard import check_expiry_guard
from signal_engine import build_verdict
from alert_rules import check_events
from alert_notifier import send_alert, notify_telegram
import storage
from main import format_output  # переиспользуем готовый форматтер вывода


def run_once(send_snapshots_to_telegram: bool = False):
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

    output_text = format_output(parsed, iv_result, melt_result, confluence, expiry_result, verdict)
    print("\n" + output_text)

    if send_snapshots_to_telegram:
        notify_telegram(output_text)

    events = check_events(parsed, previous, verdict, melt_result, iv_result)
    if events:
        print(f"\n🔔 Отправляю {len(events)} алерт(ов)...")
        for ev in events:
            send_alert(ev["title"], ev["message"])
    else:
        print("\n(значимых событий для алерта нет)")

    storage.save_snapshot(parsed)
    print(f"\n(снапшот сохранён, всего в истории: {storage.count_snapshots()})")


def seconds_until_next_boundary(interval_sec: int) -> float:
    """
    Секунды до ближайшей "круглой" отметки по часам (например :00 :15 :30 :45
    при interval_sec=900). Считается от начала текущих суток UTC, чтобы
    отметки были предсказуемыми и совпадали с ожиданиями пользователя.
    """
    now = datetime.now(timezone.utc)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = (now - midnight).total_seconds()
    remainder = elapsed % interval_sec
    wait = interval_sec - remainder if remainder > 0 else 0
    return wait


def main():
    tg_snapshots = "--no-tg-snapshots" not in sys.argv

    if "--loop" in sys.argv:
        idx = sys.argv.index("--loop")
        interval = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 900
        print(f"Автономный режим: обновление каждые {interval} сек, строго по часам. Ctrl+C для остановки.")
        if tg_snapshots:
            print("Каждый снапшот будет отправляться в Telegram целиком.")

        # первый запуск — сразу, для проверки, что всё работает
        run_once(send_snapshots_to_telegram=tg_snapshots)

        while True:
            wait = seconds_until_next_boundary(interval)
            print(f"\n⏳ Следующий снапшот через {int(wait)} сек...")
            time.sleep(wait)
            run_once(send_snapshots_to_telegram=tg_snapshots)
    else:
        # разовый запуск — снапшот в Telegram шлём тоже, если явно не отключили
        run_once(send_snapshots_to_telegram=tg_snapshots)


if __name__ == "__main__":
    main()
