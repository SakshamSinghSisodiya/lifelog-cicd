import os
import random
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
    """Sample data relative to today so every fresh pod looks alive."""
    rng = random.Random(42)
    today = date.today()
    # (name, forced current run in days, chance of a hit on older days)
    habits = [("Drink 2L water", 6, 0.8), ("Read 20 minutes", 3, 0.65), ("Evening walk", 0, 0.5),
              ("Meditate 10 min", 11, 0.7), ("Journal", 1, 0.55)]
    for name, run, chance in habits:
        habit_id = conn.execute("INSERT INTO habits (name) VALUES (?)", (name,)).lastrowid
        for i in range(45):
            hit = i < run or (i > run and rng.random() < chance)
            if hit:
                conn.execute("INSERT INTO checkins VALUES (?, ?)", (habit_id, (today - timedelta(days=i)).isoformat()))
    categories = ["Food", "Food", "Food", "Transport", "Home", "Fun", "Health"]
    for i in range(30):
        for _ in range(rng.choice([0, 1, 1, 2])):
            category = rng.choice(categories)
            amount = round(rng.uniform(4, 28) if category != "Home" else rng.uniform(25, 70), 2)
            conn.execute("INSERT INTO expenses (amount, category, day) VALUES (?, ?, ?)",
                         (amount, category, (today - timedelta(days=i)).isoformat()))
    conn.execute("INSERT INTO budgets VALUES (?, ?)", (today.strftime("%Y-%m"), 650.0))
    goals = [("Read 12 books", 12, 5, 120), ("Save $1000", 1000, 640, 60), ("Run 100 km", 100, 38, 30)]
    for name, target, progress, days_ahead in goals:
        conn.execute("INSERT INTO goals (name, target, progress, deadline) VALUES (?, ?, ?, ?)",
                     (name, target, progress, (today + timedelta(days=days_ahead)).isoformat()))
