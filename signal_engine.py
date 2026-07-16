# -*- coding: utf-8 -*-
"""
signal_engine.py
Сводит все модули (IV, стены, confluence, expiry guard, checklist, сценарии)
в один финальный вердикт: STRONG / MODERATE / WEAK / NO SIGNAL
+ явное заходить / не заходить + направление (CALL/PUT/ожидание).
"""


def build_verdict(parsed: dict, iv_result: dict, melt_result: dict,
                   confluence: list, expiry_result: dict):

    score = 0.0
    reasons = []

    # 1. Conviction score из самого отчёта (вес 0.35)
    conv = parsed.get("conviction_score")
    if conv is not None:
        score += (conv / 100) * 35
        reasons.append(f"Conviction Score {conv}/100")

    # 2. Checklist pass ratio (вес 0.2)
    cp, ct = parsed.get("checklist_pass"), parsed.get("checklist_total")
    if cp is not None and ct:
        ratio = cp / ct
        score += ratio * 20
        reasons.append(f"Checklist {cp}/{ct}")

    # 3. IV zone (вес 0.2) — для покупателя опционов низкая IV лучше
    if iv_result.get("available") and iv_result.get("full_verdict"):
        pct = iv_result.get("percentile_used") or 50
        iv_score = max(0, (100 - pct)) / 100 * 20
        score += iv_score
        reasons.append(f"IV zone {iv_result['zone_icon']} ({pct}-й перцентиль)")
    elif iv_result.get("available"):
        reasons.append("IV: недостаточно истории для полного вердикта (нужно 10 снапшотов)")

    # 4. Confluence стен с Volume Profile (вес 0.15)
    if confluence:
        score += min(len(confluence), 2) * 7.5
        reasons.append(f"Confluence: {', '.join(confluence)}")

    # 5. Wall melt (вес 0.1) — тающая стена в сторону сценария усиливает сигнал
    melt_bonus = 0
    for wall_key in ("call_wall", "put_wall"):
        w = melt_result.get(wall_key)
        if w and w.get("status") == "melting":
            melt_bonus += 5
            reasons.append(f"{wall_key}: тает ({w.get('change_pct')}%)")
        elif w and w.get("status") == "building":
            reasons.append(f"{wall_key}: укрепляется ({w.get('change_pct')}%)")
    score += melt_bonus

    # 6. Expiry guard — штраф, а не обнуление
    if expiry_result.get("flagged"):
        score *= 0.7
        reasons.append(f"⚠ Expiry guard: {expiry_result['reason']}")

    score = round(min(score, 100), 1)

    # Направление по сценариям и смещению рынка
    up_pct = parsed.get("scenario_up_pct")
    down_pct = parsed.get("scenario_down_pct")
    direction = "нейтрально"
    if up_pct is not None and down_pct is not None:
        if up_pct - down_pct >= 15:
            direction = "CALL (в сторону роста)"
        elif down_pct - up_pct >= 15:
            direction = "PUT (в сторону падения)"

    if score >= 70:
        grade = "STRONG"
    elif score >= 55:
        grade = "MODERATE"
    elif score >= 40:
        grade = "WEAK"
    else:
        grade = "NO SIGNAL"

    enter = grade in ("STRONG", "MODERATE") and direction != "нейтрально" and not expiry_result.get("flagged", False)
    # даже при флаге экспирации не блокируем полностью, но требуем STRONG
    if expiry_result.get("flagged") and grade == "STRONG" and direction != "нейтрально":
        enter = True

    verdict_text = "✅ ЗАХОДИТЬ" if enter else "🚫 НЕ ЗАХОДИТЬ"

    return {
        "score": score,
        "grade": grade,
        "direction": direction,
        "enter": enter,
        "verdict_text": verdict_text,
        "reasons": reasons,
    }
