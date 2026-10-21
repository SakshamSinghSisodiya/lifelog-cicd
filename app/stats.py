"""Pure statistics for trackers: streaks, completion, week cells, sparkline geometry."""
from datetime import date, timedelta

TONES = ["sage", "clay", "sand", "sky", "plum", "rose", "slate", "moss"]
TYPES = ["check", "count", "number", "mood", "money"]


def is_scheduled(days: str, day: date) -> bool:
    return str(day.weekday()) in days


def is_met(ttype: str, target, value) -> bool:
    """check: ticked; count: target reached; number/mood/money: anything logged."""
    if value is None:
        return False
    if ttype == "count":
        return value >= (target or 1)
    if ttype == "check":
        return value > 0
    return True


def streaks(ttype, target, days, values: dict[date, float], today: date) -> tuple[int, int]:
    """(current, best) over scheduled days. Unscheduled days never break a streak,
    and a scheduled today that is not done yet does not break it either."""
    if ttype not in ("check", "count") or not values:
        return 0, 0
    first = min(values)
    current, day = 0, today
    while day >= first:
        if is_scheduled(days, day):
            if is_met(ttype, target, values.get(day)):
                current += 1
            elif day != today:
                break
        day -= timedelta(days=1)
    best = run = 0
    day = first
    while day <= today:
        if is_scheduled(days, day):
            if is_met(ttype, target, values.get(day)):
                run += 1
                best = max(best, run)
            elif day != today:
                run = 0
        day += timedelta(days=1)
    return current, best


def completion_rate(ttype, target, days, values, today, window=30) -> int:
    due = [today - timedelta(days=i) for i in range(window) if is_scheduled(days, today - timedelta(days=i))]
    if not due:
        return 0
    return round(sum(is_met(ttype, target, values.get(d)) for d in due) / len(due) * 100)


def cells(ttype, target, days, values, end: date, n: int) -> list[dict]:
    """One cell per day, oldest first. state: met | part | miss | off."""
    out = []
    for i in range(n - 1, -1, -1):
        day = end - timedelta(days=i)
        value = values.get(day)
        if is_met(ttype, target, value):
            state = "met"
        elif ttype == "count" and value:
            state = "part"
        elif not is_scheduled(days, day) and value is None:
            state = "off"
        else:
            state = "miss"
        out.append({"day": day, "state": state, "value": value})
    return out


def sparkline(values: list, width=240, height=56, pad=5) -> dict:
    """Polyline points and dots for the non-empty values (None = no entry that day)."""
    known = [v for v in values if v is not None]
    if not known:
        return {"points": "", "dots": []}
    lo, hi = min(known), max(known)
    span = (hi - lo) or 1
    step = (width - 2 * pad) / max(len(values) - 1, 1)
    dots = [
        (round(pad + i * step, 1), round(height - pad - (v - lo) / span * (height - 2 * pad), 1))
        for i, v in enumerate(values) if v is not None
    ]
    return {"points": " ".join(f"{x},{y}" for x, y in dots), "dots": dots}
