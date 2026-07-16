# -*- coding: utf-8 -*-
"""
report_parser.py
Разбор вставленного текстового отчёта (формат "Institutional BTC Options Report")
в структурированный dict. Устойчив к небольшим отличиям в пробелах/переносах.
"""

import re
from datetime import datetime


def _num(s):
    if s is None:
        return None
    s = s.strip().replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _first(pattern, text, flags=re.IGNORECASE):
    m = re.search(pattern, text, flags)
    return m


def parse_report(text: str) -> dict:
    data = {}

    m = _first(r"Snapshot\s*#(\d+)\s*\(([^)]+)\)", text)
    if m:
        data["snapshot_num"] = int(m.group(1))
        data["ts_raw"] = m.group(2).strip()
        data["ts_iso"] = _parse_ts(m.group(2).strip())
    else:
        data["snapshot_num"] = None
        data["ts_raw"] = None
        data["ts_iso"] = None

    # Таблица "Состояние рынка" — берём первое вхождение метки с числом сразу после неё
    m = _first(r"Цена\s+([\d\s]{3,8})\s", text)
    data["price"] = _num(m.group(1)) if m else None

    m = _first(r"VWAP\s+([\d\s]{3,8})\s", text)
    data["vwap"] = _num(m.group(1)) if m else None

    m = _first(r"POC\s+([\d\s]{3,8})\s", text)
    data["poc"] = _num(m.group(1)) if m else None

    m = _first(r"Value Area\s+([\d\s]{3,8})\s*[–\-]\s*([\d\s]{3,8})", text)
    if m:
        data["val"] = _num(m.group(1))
        data["vah"] = _num(m.group(2))
    else:
        data["val"] = data["vah"] = None

    m = _first(r"PCR\s+([\d]+[.,]?\d*)", text)
    data["pcr"] = _num(m.group(1)) if m else None

    m = _first(r"ATM\s*IV\s+([\d]+[.,]?\d*)\s*%", text)
    data["atm_iv"] = _num(m.group(1)) if m else None

    m = _first(r"Above\s*:\s*Call\s*(\d+)", text)
    data["above_call"] = int(m.group(1)) if m else None

    m = _first(r"At\s*:\s*Call\s*(\d+)\s*\|\s*Put\s*(\d+)", text)
    if m:
        data["at_call"] = int(m.group(1))
        data["at_put"] = int(m.group(2))
    else:
        data["at_call"] = data["at_put"] = None

    m = _first(r"Below\s*:\s*Put\s*(\d+)", text)
    data["below_put"] = int(m.group(1)) if m else None

    m = _first(r"([\d\s]{3,8})\s*[—\-]\s*Max Put OI\s*\((\d+)\)", text)
    if m:
        data["max_put_oi_strike"] = _num(m.group(1))
        data["max_put_oi_value"] = int(m.group(2))
    else:
        data["max_put_oi_strike"] = data["max_put_oi_value"] = None

    m = _first(r"([\d\s]{3,8})\s*[—\-]\s*Max Call OI\s*\((\d+)\)", text)
    if m:
        data["max_call_oi_strike"] = _num(m.group(1))
        data["max_call_oi_value"] = int(m.group(2))
    else:
        data["max_call_oi_strike"] = data["max_call_oi_value"] = None

    # Уровни поддержки/сопротивления (список строк вида "65064 — VWAP")
    data["support_levels"] = _parse_levels(text, "Поддержка", "Сопротивление")
    data["resistance_levels"] = _parse_levels(text, "Сопротивление", "Вероятные сценарии")

    m = _first(r"Conviction Score:\s*(\d+)\s*/\s*100", text)
    data["conviction_score"] = int(m.group(1)) if m else None

    m = _first(r"OI Confidence:\s*([⭐☆]+)", text)
    data["oi_confidence_stars"] = m.group(1).count("⭐") if m else None

    m = _first(r"Market Bias\s*\n+\s*(?:🟢|🟡|🔴)?\s*([^\n]+)", text)
    data["market_bias"] = m.group(1).strip() if m else None

    m = _first(r"Подтверждение роста:\s*(\d+)\s*/\s*(\d+)", text)
    if m:
        data["checklist_pass"] = int(m.group(1))
        data["checklist_total"] = int(m.group(2))
    else:
        data["checklist_pass"] = data["checklist_total"] = None

    m = _first(r"Продолжение роста\s*[—\-]\s*(\d+)\s*%", text)
    data["scenario_up_pct"] = int(m.group(1)) if m else None

    m = _first(r"Коррекция\s*[—\-]\s*(\d+)\s*%", text)
    data["scenario_down_pct"] = int(m.group(1)) if m else None

    data["raw_text"] = text
    return data


def _parse_levels(text, section_label, next_label):
    m = re.search(rf"{section_label}\s*\n(.*?)(?:{next_label}|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1)
    levels = []
    for line in block.splitlines():
        lm = re.match(r"\s*([\d\s]{3,8})\s*[—\-]\s*(.+)", line)
        if lm:
            val = _num(lm.group(1))
            if val:
                levels.append({"level": val, "label": lm.group(2).strip()})
    return levels


def _parse_ts(raw: str):
    # ожидаем формат "16.07.2026 01:00"
    try:
        dt = datetime.strptime(raw.strip(), "%d.%m.%Y %H:%M")
        return dt.isoformat()
    except ValueError:
        return None
