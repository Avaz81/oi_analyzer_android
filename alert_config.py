# -*- coding: utf-8 -*-
"""
alert_config.py
Читает секреты (Telegram bot token / chat_id) из локального файла
secrets.json, который НЕ загружается на GitHub (см. .gitignore и README).
Если файла нет — Telegram-алерты просто отключаются, Termux всё равно работает.
"""

import json
import os

SECRETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.json")

_cached = None


def load_config():
    global _cached
    if _cached is not None:
        return _cached

    if not os.path.exists(SECRETS_PATH):
        _cached = {"telegram_token": None, "telegram_chat_id": None}
        return _cached

    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {}

    _cached = {
        "telegram_token": data.get("telegram_token"),
        "telegram_chat_id": data.get("telegram_chat_id"),
    }
    return _cached
