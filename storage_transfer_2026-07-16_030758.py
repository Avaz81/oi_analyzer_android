# -*- coding: utf-8 -*-
"""
storage.py
Хранилище снапшотов в SQLite. Работает офлайн, без внешних API.
База лежит рядом со скриптом: oi_analyzer.db
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oi_analyzer.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_num INTEGER,
    ts_raw TEXT,
    ts_iso TEXT,
    price REAL,
    vwap REAL,
    poc REAL,
    val REAL,
    vah REAL,
    pcr REAL,
    atm_iv REAL,
    above_call INTEGER,
    at_call INTEGER,
    at_put INTEGER,
    below_put INTEGER,
    max_call_oi_strike REAL,
    max_call_oi_value INTEGER,
    max_put_oi_strike REAL,
    max_put_oi_value INTEGER,
    conviction_score INTEGER,
    oi_confidence_stars INTEGER,
    market_bias TEXT,
    checklist_pass INTEGER,
    checklist_total INTEGER,
    scenario_up_pct INTEGER,
    scenario_down_pct INTEGER,
    raw_text TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def save_snapshot(data: dict) -> int:
    conn = get_conn()
    cols = [
        "snapshot_num", "ts_raw", "ts_iso", "price", "vwap", "poc", "val", "vah",
        "pcr", "atm_iv", "above_call", "at_call", "at_put", "below_put",
        "max_call_oi_strike", "max_call_oi_value", "max_put_oi_strike", "max_put_oi_value",
        "conviction_score", "oi_confidence_stars", "market_bias",
        "checklist_pass", "checklist_total", "scenario_up_pct", "scenario_down_pct",
        "raw_text",
    ]
    values = [data.get(c) for c in cols]
    placeholders = ",".join(["?"] * len(cols))
    cur = conn.execute(
        f"INSERT INTO snapshots ({','.join(cols)}) VALUES ({placeholders})", values
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_last(n: int, before_id: int = None):
    conn = get_conn()
    if before_id:
        rows = conn.execute(
            "SELECT * FROM snapshots WHERE id < ? ORDER BY id DESC LIMIT ?",
            (before_id, n),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_iv_history(limit: int = 90):
    conn = get_conn()
    rows = conn.execute(
        "SELECT atm_iv, ts_iso FROM snapshots WHERE atm_iv IS NOT NULL "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [r["atm_iv"] for r in rows if r["atm_iv"] is not None]


def count_snapshots():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM snapshots").fetchone()["c"]
    conn.close()
    return n
