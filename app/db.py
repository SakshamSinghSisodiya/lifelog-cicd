import os
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS trackers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('check', 'count', 'number', 'mood', 'money')),
    color TEXT NOT NULL DEFAULT 'sage',
    unit TEXT NOT NULL DEFAULT '',
    target REAL,                              -- daily target; for money, the monthly budget
    days TEXT NOT NULL DEFAULT '0123456',     -- scheduled weekdays, Monday = 0
    archived INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entries (          -- one row per tracker per day, except money (many)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracker_id INTEGER NOT NULL REFERENCES trackers(id),
    day TEXT NOT NULL,
    value REAL NOT NULL,
    category TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entries_tracker_day ON entries(tracker_id, day);
CREATE INDEX IF NOT EXISTS idx_entries_day ON entries(day);
CREATE TABLE IF NOT EXISTS actions (          -- what the capture bar did, so "undo" can reverse it
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                       -- set | money | create
    tracker_id INTEGER,
    day TEXT,
    prev_value REAL,
    entry_id INTEGER,
    label TEXT NOT NULL,
    undone INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target REAL NOT NULL,
    progress REAL NOT NULL DEFAULT 0,
    deadline TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(path, seed=True):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if seed and conn.execute("SELECT COUNT(*) FROM trackers").fetchone()[0] == 0:
        from .seed import seed_demo_data

        seed_demo_data(conn)
    conn.commit()
    conn.close()
