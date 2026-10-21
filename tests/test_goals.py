from datetime import date, timedelta

from app.goals_logic import days_left, goal_status, percent_complete

TODAY = date(2026, 3, 10)


def test_percent_complete_basic_and_cap():
    assert percent_complete(25, 100) == 25.0
    assert percent_complete(150, 100) == 100.0


def test_percent_complete_zero_target_is_safe():
    assert percent_complete(5, 0) == 0.0


def test_days_left_and_status():
    assert days_left(TODAY + timedelta(days=5), TODAY) == 5
    assert goal_status(10, 10, TODAY, TODAY) == "done"
    assert goal_status(1, 10, TODAY - timedelta(days=1), TODAY) == "late"
    assert goal_status(1, 10, TODAY + timedelta(days=1), TODAY) == "active"


def test_goals_page_and_nav_link(client):
    html = client.get("/goals").get_data(as_text=True)
    assert "New goal" in html
    assert "/goals" in client.get("/").get_data(as_text=True)


def test_add_goal_and_progress(client):
    deadline = (date.today() + timedelta(days=30)).isoformat()
    client.post("/goals", data={"name": "Read books", "target": "12", "deadline": deadline})
    client.post("/goals/1/progress", data={"amount": "3"})
    html = client.get("/goals").get_data(as_text=True)
    assert "Read books" in html and "25.0%" in html


def test_invalid_goal_rejected(client):
    resp = client.post("/goals", data={"name": "", "target": "5", "deadline": "2030-01-01"}, follow_redirects=True)
    assert "positive target" in resp.get_data(as_text=True)
