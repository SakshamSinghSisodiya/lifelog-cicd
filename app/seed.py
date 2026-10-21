"""Demo data relative to today, so every fresh pod opens with a lived-in log."""
import random
from datetime import date, timedelta

from . import service

WEEKDAYS_ONLY = "0123456"


def seed_demo_data(conn):
    rng = random.Random(7)
    today = date.today()
    specs = [
        # name, type, color, unit, target, scheduled days
        ("Gym", "check", "clay", "", 1, "0246"),
        ("Read", "check", "sky", "", 1, WEEKDAYS_ONLY),
        ("Water", "count", "sage", "glasses", 8, WEEKDAYS_ONLY),
        ("Sleep", "number", "plum", "h", None, WEEKDAYS_ONLY),
        ("Weight", "number", "slate", "kg", None, WEEKDAYS_ONLY),
        ("Mood", "mood", "sand", "", None, WEEKDAYS_ONLY),
        ("Spending", "money", "moss", "", 9000, WEEKDAYS_ONLY),
    ]
    ids = {}
    for name, ttype, color, unit, target, days in specs:
        ids[name] = service.create_tracker(conn, name, ttype, color, unit, target, days)

    for i in range(60, -1, -1):
        day = today - timedelta(days=i)
        recent = i < 8  # keep the most recent week tidy so streaks look real
        if str(day.weekday()) in "0246" and (recent and i > 0 or rng.random() < 0.7):
            service.write_value(conn, ids["Gym"], day, 1.0)
        if i > 0 and rng.random() < (0.9 if recent else 0.65):
            service.write_value(conn, ids["Read"], day, 1.0)
        water = 3.0 if i == 0 else float(rng.randint(8, 9) if recent else rng.randint(3, 10))
        service.write_value(conn, ids["Water"], day, water)
        if i > 0:
            service.write_value(conn, ids["Sleep"], day, round(rng.uniform(5.8, 8.4), 1))
            service.write_value(conn, ids["Mood"], day, float(rng.choice([3, 3, 4, 4, 4, 5, 2])))
        if i % 3 == 0:
            service.write_value(conn, ids["Weight"], day, round(72.6 - (60 - i) * 0.02 + rng.uniform(-0.3, 0.3), 1))
        for _ in range(rng.choice([0, 1, 1, 2])):
            category = rng.choice(["Food", "Food", "Food", "Transport", "Study", "Fun", "Bills", "Other"])
            amount = round(rng.uniform(60, 260) if category != "Bills" else rng.uniform(300, 900), 0)
            service.write_money(conn, ids["Spending"], day, amount, category, "")
    conn.commit()
    for name, target, progress, days_ahead in [("Read 12 books", 12, 5, 120), ("Save 40000", 40000, 26500, 60), ("Run 100 km", 100, 38, 30)]:
        conn.execute("INSERT INTO goals (name, target, progress, deadline) VALUES (?, ?, ?, ?)",
                     (name, target, progress, (today + timedelta(days=days_ahead)).isoformat()))
    conn.commit()
