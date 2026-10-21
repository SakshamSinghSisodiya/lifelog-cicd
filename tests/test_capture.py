from datetime import date

import pytest

from app.capture import parse

TODAY = date(2026, 10, 21)  # a Wednesday
TRACKERS = [
    {"id": 1, "name": "Gym", "type": "check"},
    {"id": 2, "name": "Water", "type": "count"},
    {"id": 3, "name": "Sleep", "type": "number"},
    {"id": 4, "name": "Mood", "type": "mood"},
    {"id": 5, "name": "Spending", "type": "money"},
    {"id": 6, "name": "Read", "type": "check"},
    {"id": 7, "name": "Reflect", "type": "check"},
]


def p(text, trackers=TRACKERS):
    return parse(text, trackers, TODAY)


def test_check_by_name_and_with_done():
    for text in ("gym", "gym done", "did gym"):
        i = p(text)
        assert (i.kind, i.tracker["name"], i.value) == ("set", "Gym", 1.0)


def test_check_undone_clears():
    assert p("gym undone").value == 0.0
    assert p("gym 0").value == 0.0


def test_count_adds_with_or_without_plus():
    assert (p("water 3").kind, p("water 3").value) == ("add", 3.0)
    assert p("water +3").value == 3.0
    assert p("water").value == 1.0


def test_count_can_subtract_and_set():
    assert p("water -1").value == -1.0
    i = p("water =5")
    assert (i.kind, i.value) == ("set", 5.0)


def test_number_sets_value_and_needs_one():
    assert (p("sleep 7.5").kind, p("sleep 7.5").value) == ("set", 7.5)
    assert p("sleep").kind == "error"


def test_number_accepts_unit_suffix():
    assert p("sleep 7.5h").value == 7.5


def test_mood_range_and_whole_numbers():
    assert p("mood 4").value == 4.0
    assert p("mood 6").kind == "error"
    assert p("mood 3.5").kind == "error"


@pytest.mark.parametrize("text,amount,category", [
    ("spent 250 lunch", 250, "Food"),
    ("250 food", 250, "Food"),
    ("-250 uber", 250, "Transport"),
    ("paid 1,200 rent", 1200, "Bills"),
    ("spent 99 mystery", 99, "Other"),
    ("₹80 chai", 80, "Food"),
    ("spent 400 udemy course", 400, "Study"),
])
def test_money_forms_and_categories(text, amount, category):
    i = p(text)
    assert (i.kind, i.value, i.category) == ("money", amount, category)
    assert i.tracker["name"] == "Spending"


def test_money_note_keeps_words():
    assert p("spent 250 team lunch").note == "team lunch"


def test_money_tracker_by_name_with_note():
    i = p("spending 120 movie")
    assert (i.kind, i.value, i.category) == ("money", 120, "Fun")


def test_money_without_tracker_offers_create():
    i = parse("spent 50 lunch", [t for t in TRACKERS if t["type"] != "money"], TODAY)
    assert i.kind == "error" and i.create == {"name": "Spending", "type": "money"}


def test_spent_without_amount_is_error():
    assert p("spent lunch").kind == "error"


def test_yesterday_either_side():
    assert p("yesterday gym").day == date(2026, 10, 20)
    assert p("gym yesterday").day == date(2026, 10, 20)


def test_weekday_means_most_recent_before_today():
    assert p("gym mon").day == date(2026, 10, 19)
    assert p("gym wed").day == date(2026, 10, 14)  # today is Wed, so last week's
    assert p("tue water 2").day == date(2026, 10, 20)


def test_today_word_is_accepted():
    assert p("gym today").day == TODAY


def test_unique_prefix_matches():
    assert p("wat 2").tracker["name"] == "Water"
    assert p("sl 6").tracker["name"] == "Sleep"


def test_ambiguous_prefix_gives_suggestions():
    i = p("re")
    assert i.kind == "ambiguous"
    assert {s["label"] for s in i.suggestions} == {"Read", "Reflect"}


def test_fuzzy_typo_is_corrected():
    assert p("watr 3").tracker["name"] == "Water"


def test_case_insensitive():
    assert p("GyM").tracker["name"] == "Gym"


def test_unknown_offers_create_with_guessed_type():
    i = p("pushups 20")
    assert i.kind == "unknown"
    assert i.create == {"name": "Pushups", "type": "count"}
    assert p("yoga").create == {"name": "Yoga", "type": "check"}
    assert p("weight 72.5").create["type"] == "number"


def test_unknown_with_near_match_suggests_it():
    i = p("sleeo")
    assert i.tracker is not None or any(s["label"] == "Sleep" for s in i.suggestions)


def test_undo_and_empty():
    assert p("undo").kind == "undo"
    assert p("   ").kind == "empty"


def test_name_starting_with_filler_word_is_kept():
    trackers = TRACKERS + [{"id": 9, "name": "No sugar", "type": "check"}]
    assert p("no sugar", trackers).tracker["name"] == "No sugar"


def test_note_after_tracker_name():
    i = p("gym legs day")
    assert i.tracker["name"] == "Gym" and i.note == "legs day"
