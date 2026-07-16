# -*- coding: utf-8 -*-
"""
alert_rules.py
Определяет, какие события достаточно значимы, чтобы прислать алерт:
  - вердикт ЗАХОДИТЬ (STRONG/MODERATE + направление)
  - таяние OI-стены
  - резкий скачок ATM IV между снапшотами
  - пробитие ключевого уровня (VWAP / POC / VAH / VAL)
"""

IV_SPIKE_THRESHOLD_PCT = 15.0  # относительное изменение IV между снапшотами


def check_events(parsed, previous, verdict, melt_result, iv_result):
    events = []

    # 1. Вердикт на вход
    if verdict.get("enter"):
        events.append({
            "title": "✅ Сигнал на вход",
            "message": (
                f"Snapshot #{parsed.get('snapshot_num')} | "
                f"Score {verdict['score']}/100 ({verdict['grade']}) | "
                f"{verdict['direction']}\n"
                f"Цена {parsed.get('price')}"
            ),
        })

    # 2. Таяние стен
    for key, label in (("call_wall", "Call wall"), ("put_wall", "Put wall")):
        w = melt_result.get(key)
        if w and w.get("status") == "melting":
            events.append({
                "title": f"⚠ {label} тает",
                "message": f"Изменение OI: {w.get('change_pct')}% — возможен пробой уровня",
            })

    # 3. Резкий скачок IV
    if previous and previous.get("atm_iv") and parsed.get("atm_iv"):
        prev_iv = previous["atm_iv"]
        cur_iv = parsed["atm_iv"]
        if prev_iv:
            pct = (cur_iv - prev_iv) / prev_iv * 100
            if abs(pct) >= IV_SPIKE_THRESHOLD_PCT:
                direction = "рост" if pct > 0 else "падение"
                events.append({
                    "title": f"⚡ Резкий скачок IV ({direction})",
                    "message": f"ATM IV: {prev_iv}% → {cur_iv}% ({pct:+.1f}%)",
                })

    # 4. Пробитие ключевого уровня (сравниваем сторону цены относительно уровня)
    if previous and parsed.get("price") is not None and previous.get("price") is not None:
        for level_name in ("vwap", "poc", "vah", "val"):
            lvl = parsed.get(level_name)
            prev_lvl = previous.get(level_name)
            if lvl is None or prev_lvl is None:
                continue
            was_above = previous["price"] > prev_lvl
            now_above = parsed["price"] > lvl
            if was_above != now_above:
                direction = "выше" if now_above else "ниже"
                events.append({
                    "title": f"🚧 Пробитие уровня {level_name.upper()}",
                    "message": f"Цена {parsed['price']} теперь {direction} {level_name.upper()} ({lvl})",
                })

    return events
