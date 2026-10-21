"""Pure budget maths for the Expenses module."""


def month_of(day_iso: str) -> str:
    return day_iso[:7]


def totals_by_category(expenses, month: str) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in expenses:
        if month_of(item["day"]) == month:
            totals[item["category"]] = totals.get(item["category"], 0.0) + item["amount"]
    return {k: round(v, 2) for k, v in sorted(totals.items())}


def percent_used(spent: float, budget: float) -> float:
    if budget <= 0:
        return 0.0
    return round(spent / budget * 100, 1)


def budget_status(percent: float) -> str:
    if percent >= 100:
        return "over"
    return "warn" if percent >= 80 else "ok"
