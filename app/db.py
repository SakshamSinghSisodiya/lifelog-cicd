import os
import sqlite3
from datetime import date, timedelta

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    habit_id INTEGER NOT NULL REFERENCES habits(id),
    day TEXT NOT NULL,
    PRIMARY KEY (habit_id, day)
);
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    day TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS budgets (
    month TEXT PRIMARY KEY,
    amount REAL NOT NULL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM habits").fetchone()[0] == 0:
        seed(conn)
    conn.commit()
    conn.close()


def seed(conn):
    today = date.today()
    habits = {"Drink 2L water": 6, "Read 20 minutes": 3, "Evening walk": 0}
    for name, run in habits.items():
        cur = conn.execute("INSERT INTO habits (name) VALUES (?)", (name,))
        for i in range(run):
            day = (today - timedelta(days=i)).isoformat()
            conn.execute("INSERT INTO checkins VALUES (?, ?)", (cur.lastrowid, day))
    month = today.strftime("%Y-%m")
    samples = [(42.5, "Food", 1), (18.0, "Transport", 2), (60.0, "Fun", 3), (25.0, "Food", 4)]
    for amount, category, offset in samples:
        day = today.replace(day=1) + timedelta(days=min(offset, 20))
        if day > today:
            day = today
        conn.execute(
            "INSERT INTO expenses (amount, category, day) VALUES (?, ?, ?)",
            (amount, category, day.isoformat()),
        )
    conn.execute("INSERT INTO budgets VALUES (?, ?)", (month, 400.0))
