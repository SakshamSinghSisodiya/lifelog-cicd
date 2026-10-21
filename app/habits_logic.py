"""Pure streak maths: no Flask or database, so it is easy to unit-test."""
from datetime import date, timedelta


def current_streak(days: set[date], today: date) -> int:
    # Today not ticked yet should not break a streak that ran up to yesterday.
    cursor = today if today in days else today - timedelta(days=1)
    count = 0
    while cursor in days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def longest_streak(days: set[date]) -> int:
    best = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


def parse_days(rows) -> set[date]:
    return {date.fromisoformat(r) for r in rows}
