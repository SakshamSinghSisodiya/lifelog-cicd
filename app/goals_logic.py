"""Pure goal maths for the Goals module (v2)."""
from datetime import date


def percent_complete(current: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return round(min(current / target * 100, 100), 1)


def days_left(deadline: date, today: date) -> int:
    return (deadline - today).days


def goal_status(current: float, target: float, deadline: date, today: date) -> str:
    if target > 0 and current >= target:
        return "done"
    return "late" if deadline < today else "active"
