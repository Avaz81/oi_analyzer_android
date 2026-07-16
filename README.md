# oi_analyzer_android — планировщик-анализатор для Termux

## Установка (Termux, Android)
```
pkg install python
```
(sqlite3 уже входит в стандартную библиотеку Python — доп. пакеты не нужны)

Скопируй папку `oi_analyzer_android/` на телефон в Termux (через termux-storage, git, или просто вручную).

## Запуск
```
cd oi_analyzer_android
python3 main.py
```
Вставь текст отчёта (тот же формат, что выдаёт oi_monitor на Windows), в конце
введи `END` и нажми Enter.

## Что делает
- Парсит отчёт (цена, VWAP, POC, Value Area, PCR, ATM IV, OI-стены, checklist, сценарии).
- Считает IV Rank/Percentile по накопленной истории (нужно 10 снапшотов для полного вердикта,
  дальше используется адаптивное окно 10/30 снапшотов) — зона 🟢/🟡/🟠/🔴.
- Сравнивает текущие OI-стены с предыдущим снапшотом → тает / укрепляется / сместилась.
- Проверяет confluence стен с POC/VWAP/VAH/VAL.
- Expiry guard: флагует снапшоты в пределах 45 мин от дневной экспирации (11:00 МСК).
- Сводит всё в единый Score/Grade (STRONG/MODERATE/WEAK/NO SIGNAL) и явный
  вердикт: ✅ ЗАХОДИТЬ / 🚫 НЕ ЗАХОДИТЬ + направление (CALL/PUT/нейтрально).
- Каждый вставленный снапшот сохраняется в `oi_analyzer.db` (SQLite) — база растёт
  сама по себе, отдельно синхронизировать с Windows-версией не нужно.

## Файлы
- `main.py` — точка входа (CLI, ввод отчёта, вывод анализа)
- `report_parser.py` — парсинг текста отчёта в dict
- `iv_analyzer.py` — IV Rank/Percentile
- `wall_analyzer.py` — wall melt + confluence
- `expiry_guard.py` — защита от шума у экспирации
- `signal_engine.py` — финальный вердикт
- `storage.py` — SQLite хранилище истории снапшотов

## Автономный режим (без ручной вставки отчёта)
Новые файлы `live_deribit.py`, `live_bybit.py`, `live_report_builder.py`, `main_live.py`
сами тянут данные: OI/IV/страйки с публичного API Deribit, цену/VWAP/Volume Profile
с публичного API Bybit. Ключи и авторизация не нужны — это открытые market-data эндпоинты.

Установка (доп. к обычной):
```
pip install requests --break-system-packages
```

Разовый запуск:
```
python3 main_live.py
```

Запуск в цикле, например каждые 15 минут (900 сек):
```
python3 main_live.py --loop 900
```

Чек-лист (conviction score, market bias, сценарии up/down%) в live-режиме считается
автоматически по объективным условиям (цена vs VWAP/POC/Value Area, динамика OI,
уровень PCR) — это упрощённая эвристика, не точная копия твоего ручного анализа
из Windows-версии, но по той же логике "заходить/не заходить".

⚠ Эти live-модули написаны по документации API Deribit/Bybit, но не протестированы
живым запросом (в среде, где я их писал, нет доступа к deribit.com/bybit.com).
Первый запуск лучше сделать и прислать мне вывод/ошибку — поправлю на месте, если
что-то в структуре ответа API не совпало.

## Дальше можно добавить
- Termux:Widget / Termux:Tasker для запуска по расписанию или в один тап.
- Автовставку из буфера обмена (`termux-clipboard-get`) вместо ручного ввода (для режима с вставкой отчёта).
- termux-wake-lock, чтобы `--loop` не засыпал при выключенном экране.
