from datetime import date, timedelta

from app.insights import category_shares, completion_rate, daily_totals, projected_spend, quote_for, week_flags

TODAY = date(2026, 3, 10)


def test_week_flags_oldest_first_and_marks_hits():
    flags = week_flags({TODAY, TODAY - timedelta(days=2)}, TODAY)
    assert len(flags) == 7
    assert flags[0][0] == TODAY - timedelta(days=6)
    assert [f for _, f in flags] == [False, False, False, False, True, False, True]


def test_completion_rate_percent_of_window():
    days = {TODAY - timedelta(days=i) for i in range(15)}
    assert completion_rate(days, TODAY, window=30) == 50


def test_daily_totals_sums_per_day_and_fills_gaps():
    rows = [{"day": "2026-03-10", "amount": 5.0}, {"day": "2026-03-10", "amount": 2.5}]
    out = daily_totals(rows, TODAY, n=3)
    assert [d for d, _ in out] == [date(2026, 3, 8), date(2026, 3, 9), TODAY]
    assert [v for _, v in out] == [0.0, 0.0, 7.5]


def test_category_shares_sorted_with_percent():
    shares = category_shares({"Food": 30.0, "Fun": 70.0})
    assert [s["name"] for s in shares] == ["Fun", "Food"]
    assert shares[0]["percent"] == 70


def test_category_shares_empty():
    assert category_shares({}) == []


def test_projected_spend_scales_to_month_length():
    assert projected_spend(100.0, date(2026, 3, 10)) == 310.0


def test_quote_is_stable_per_day():
    assert quote_for(TODAY) == quote_for(TODAY)
