# -*- coding: utf-8 -*-
"""
alert_notifier.py
Отправка алертов двумя каналами:
  1. termux-notification (нативное уведомление Android) — требует пакет termux-api
     и установленное приложение Termux:API.
  2. Telegram-бот — требует secrets.json с telegram_token / telegram_chat_id.

Оба канала независимы: если один не настроен или упал с ошибкой — второй
всё равно попробует отправиться.
"""

import subprocess
import requests

from alert_config import load_config

_warned_no_telegram = False


def notify_termux(title: str, message: str):
    try:
        subprocess.run(
            ["termux-notification", "--title", title, "--content", message],
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        print("⚠ termux-notification не найден. Установи: pkg install termux-api "
              "и приложение Termux:API из F-Droid.")
    except Exception as e:
        print(f"⚠ Ошибка Termux-уведомления: {e}")


def notify_telegram(text: str):
    global _warned_no_telegram
    config = load_config()
    token, chat_id = config.get("telegram_token"), config.get("telegram_chat_id")

    if not token or not chat_id:
        if not _warned_no_telegram:
            print("ℹ Telegram-алерты не настроены (нет secrets.json) — пропускаю. "
                  "См. README, раздел 'Настройка Telegram-алертов'.")
            _warned_no_telegram = True
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=10)
        if r.status_code != 200:
            print(f"⚠ Telegram вернул ошибку {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"⚠ Ошибка отправки в Telegram: {e}")


def send_alert(title: str, message: str):
    full_text = f"{title}\n{message}"
    notify_termux(title, message)
    notify_telegram(full_text)
