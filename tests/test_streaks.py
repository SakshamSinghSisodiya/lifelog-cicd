from datetime import date, timedelta

from app.habits_logic import current_streak, longest_streak

TODAY = date(2026, 3, 10)


def days_back(*offsets):
    return {TODAY - timedelta(days=o) for o in offsets}


def test_current_streak_empty():
    assert current_streak(set(), TODAY) == 0


def test_current_streak_counts_today_and_past():
    assert current_streak(days_back(0, 1, 2), TODAY) == 3


def test_current_streak_survives_unticked_today():
    assert current_streak(days_back(1, 2), TODAY) == 2


def test_current_streak_breaks_after_gap():
    assert current_streak(days_back(2, 3), TODAY) == 0


def test_longest_streak_picks_best_run():
    assert longest_streak(days_back(0, 1, 5, 6, 7, 8)) == 4


def test_longest_streak_empty_and_single():
    assert longest_streak(set()) == 0
    assert longest_streak(days_back(3)) == 1
