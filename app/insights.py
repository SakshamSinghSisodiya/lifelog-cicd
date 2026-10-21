"""Pure helpers that turn raw rows into dashboard numbers (no Flask, no database)."""
import calendar
from datetime import date, timedelta

QUOTES = [
    "Small steps every day beat big plans someday.",
    "Fold it one crease at a time.",
    "Consistency is the quiet superpower.",
    "Track it, see it, improve it.",
    "A calm day is built from small habits.",
    "Progress, not perfection.",
    "Today's check-in is tomorrow's streak.",
]


def week_flags(days: set[date], today: date, n: int = 7) -> list[tuple[date, bool]]:
    return [(today - timedelta(days=i), (today - timedelta(days=i)) in days) for i in range(n - 1, -1, -1)]


def completion_rate(days: set[date], today: date, window: int = 30) -> int:
    hits = sum(1 for i in range(window) if today - timedelta(days=i) in days)
    return round(hits / window * 100)


def daily_totals(expenses, today: date, n: int = 14) -> list[tuple[date, float]]:
    sums: dict[str, float] = {}
    for item in expenses:
        sums[item["day"]] = sums.get(item["day"], 0.0) + item["amount"]
    out = []
    for i in range(n - 1, -1, -1):
        day = today - timedelta(days=i)
        out.append((day, round(sums.get(day.isoformat(), 0.0), 2)))
    return out


def category_shares(totals: dict[str, float]) -> list[dict]:
    grand = sum(totals.values())
    rows = [
        {"name": name, "amount": amount, "percent": round(amount / grand * 100) if grand else 0}
        for name, amount in totals.items()
    ]
    return sorted(rows, key=lambda r: r["amount"], reverse=True)


def projected_spend(spent: float, today: date) -> float:
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return round(spent / today.day * days_in_month, 2)


def quote_for(today: date) -> str:
    return QUOTES[today.toordinal() % len(QUOTES)]
