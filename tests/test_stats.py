from datetime import date, timedelta

from app.stats import cells, completion_rate, is_met, sparkline, streaks

TODAY = date(2026, 3, 11)  # Wednesday
ALL = "0123456"


def vals(*offsets, value=1.0):
    return {TODAY - timedelta(days=o): value for o in offsets}


def test_is_met_by_type():
    assert is_met("check", None, 1) and not is_met("check", None, 0)
    assert is_met("count", 8, 8) and not is_met("count", 8, 7)
    assert is_met("number", None, 0.5) and not is_met("number", None, None)


def test_streak_counts_consecutive_days_and_grace_for_today():
    assert streaks("check", None, ALL, vals(0, 1, 2), TODAY) == (3, 3)
    assert streaks("check", None, ALL, vals(1, 2), TODAY) == (2, 2)


def test_streak_breaks_on_missed_scheduled_day():
    assert streaks("check", None, ALL, vals(0, 1, 3, 4, 5), TODAY) == (2, 3)


def test_unscheduled_days_do_not_break_streak():
    mon_wed_fri = "024"  # Tue(1) is unscheduled
    values = {date(2026, 3, 11): 1.0, date(2026, 3, 9): 1.0, date(2026, 3, 6): 1.0}
    assert streaks("check", None, mon_wed_fri, values, TODAY)[0] == 3


def test_count_streak_needs_target():
    values = {TODAY: 8.0, TODAY - timedelta(days=1): 5.0}
    assert streaks("count", 8, ALL, values, TODAY) == (1, 1)


def test_streaks_only_for_check_and_count():
    assert streaks("number", None, ALL, vals(0, 1), TODAY) == (0, 0)


def test_completion_rate_over_scheduled_days_only():
    values = vals(0, 2, 4)  # done Wed, Mon, Sat (Sat is not scheduled)
    assert completion_rate("check", None, "024", values, TODAY, window=7) == 67  # due Wed, Mon, Fri: 2 of 3


def test_cells_states():
    out = cells("count", 8, "0123456", {TODAY: 3.0, TODAY - timedelta(days=1): 8.0}, TODAY, 3)
    assert [c["state"] for c in out] == ["miss", "met", "part"]


def test_cells_mark_unscheduled_days_off():
    out = cells("check", None, "0", {}, TODAY, 2)  # Tue and Wed are off
    assert [c["state"] for c in out] == ["off", "off"]


def test_sparkline_skips_missing_values():
    s = sparkline([5, None, 7], width=100, height=50, pad=5)
    assert len(s["dots"]) == 2 and s["points"].count(",") == 2


def test_sparkline_empty():
    assert sparkline([None, None])["points"] == ""
