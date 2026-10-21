from app.expenses_logic import budget_status, percent_used, totals_by_category

ITEMS = [
    {"amount": 10.0, "category": "Food", "day": "2026-03-02"},
    {"amount": 5.5, "category": "Food", "day": "2026-03-09"},
    {"amount": 20.0, "category": "Fun", "day": "2026-03-04"},
    {"amount": 99.0, "category": "Food", "day": "2026-02-28"},
]


def test_totals_group_by_category_for_month():
    assert totals_by_category(ITEMS, "2026-03") == {"Food": 15.5, "Fun": 20.0}


def test_totals_ignore_other_months():
    assert totals_by_category(ITEMS, "2026-01") == {}


def test_percent_used_basic():
    assert percent_used(150, 400) == 37.5


def test_percent_used_zero_budget_is_safe():
    assert percent_used(50, 0) == 0.0


def test_budget_status_thresholds():
    assert budget_status(40) == "ok"
    assert budget_status(85) == "warn"
    assert budget_status(100) == "over"
