#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — планировщик-анализатор для Android/Termux.

Использование:
    python3 main.py

Вставь отчёт (весь текст снапшота), затем на пустой строке введи END и Enter.
Скрипт распарсит отчёт, дополнит его недостающими блоками (IV Rank/Percentile,
wall melt, confluence, expiry guard, signal strength) и сохранит снапшот
в локальную SQLite для накопления истории (нужно для IV Rank и wall melt).

Никаких сетевых запросов не требуется — вся аналитика строится на тексте,
который ты сам вставляешь из отчёта.
"""

import sys

from report_parser import parse_report
from iv_analyzer import analyze_iv
from wall_analyzer import detect_wall_melt, detect_confluence
from expiry_guard import check_expiry_guard
from signal_engine import build_verdict
import storage


def read_report_from_stdin():
    print("Вставь текст отчёта, затем строкой END заверши ввод:\n")
    lines = []
    for line in sys.stdin:
        if line.strip() == "END":
            break
        lines.append(line.rstrip("\n"))
    return "\n".join(lines)


def format_output(parsed, iv_result, melt_result, confluence, expiry_result, verdict):
    lines = []
    lines.append("═" * 40)
    sn = parsed.get("snapshot_num")
    ts = parsed.get("ts_raw")
    lines.append(f"⚡ Быстрый анализ снапшота #{sn} ({ts})")
    lines.append("═" * 40)

    lines.append(f"Цена {parsed.get('price')} | VWAP {parsed.get('vwap')} | "
                  f"POC {parsed.get('poc')} | VA {parsed.get('val')}-{parsed.get('vah')}")
    lines.append(f"PCR {parsed.get('pcr')} | ATM IV {parsed.get('atm_iv')}%")

    lines.append("\n📈 IV Rank/Percentile")
    if iv_result.get("available"):
        if iv_result.get("full_verdict"):
            lines.append(
                f"{iv_result['zone_icon']} {iv_result['zone_text']} "
                f"(перцентиль {iv_result['percentile_used']}, "
                f"история: {iv_result['history_points']} снапшотов)"
            )
        else:
            need = 10 - iv_result["history_points"]
            lines.append(f"⚪ Накопление данных: ещё {max(need,0)} снапшотов до полного вердикта")
    else:
        lines.append("— ATM IV не найдена в отчёте")

    lines.append("\n🧱 Стены OI")
    for key, label in (("call_wall", "Call wall"), ("put_wall", "Put wall")):
        w = melt_result.get(key)
        if w is None:
            lines.append(f"{label}: нет данных для сравнения (первый снапшот в базе)")
        elif w.get("status") == "moved":
            lines.append(f"{label}: сместилась {w['from']} → {w['to']}")
        else:
            icon = {"melting": "⚠ тает", "building": "💪 растёт", "stable": "➖ стабильна"}[w["status"]]
            lines.append(f"{label}: {icon} ({w['change_pct']}%)")

    lines.append("\n🔗 Confluence со уровнями")
    lines.append(", ".join(confluence) if confluence else "совпадений не найдено")

    lines.append("\n⏱ Expiry guard")
    lines.append(expiry_result["reason"] if expiry_result.get("flagged") else "экспирация не рядом")

    lines.append("\n" + "─" * 40)
    lines.append(f"Score: {verdict['score']}/100 | Grade: {verdict['grade']} | Направление: {verdict['direction']}")
    lines.append("Причины:")
    for r in verdict["reasons"]:
        lines.append(f"  • {r}")
    lines.append("─" * 40)
    lines.append(verdict["verdict_text"])
    lines.append("═" * 40)
    return "\n".join(lines)


def main():
    text = read_report_from_stdin()
    if not text.strip():
        print("Пустой ввод, нечего анализировать.")
        return

    parsed = parse_report(text)
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
    print(f"\n(снапшот сохранён в базу, всего в истории: {storage.count_snapshots()})")


if __name__ == "__main__":
    main()
