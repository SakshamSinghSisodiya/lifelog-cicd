from datetime import date, timedelta

from app.goals_logic import days_left, goal_status, percent_complete

TODAY = date(2026, 3, 10)


def test_percent_complete_basic_and_cap():
    assert percent_complete(25, 100) == 25.0
    assert percent_complete(150, 100) == 100.0


def test_percent_complete_zero_target_is_safe():
    assert percent_complete(5, 0) == 0.0


def test_days_left():
    assert days_left(TODAY + timedelta(days=5), TODAY) == 5
    assert days_left(TODAY - timedelta(days=2), TODAY) == -2


def test_goal_status():
    assert goal_status(10, 10, TODAY, TODAY) == "done"
    assert goal_status(1, 10, TODAY - timedelta(days=1), TODAY) == "late"
    assert goal_status(1, 10, TODAY + timedelta(days=1), TODAY) == "active"


def test_goals_page_and_nav_link_on_every_page(client):
    assert "New goal" in client.get("/goals").get_data(as_text=True)
    for url in ("/", "/log", "/insights", "/trackers"):
        assert 'href="/goals"' in client.get(url).get_data(as_text=True), url


def test_add_goal_with_starting_progress_then_update(client):
    deadline = (date.today() + timedelta(days=30)).isoformat()
    client.post("/goals", data={"name": "Read books", "target": "12", "progress": "3", "deadline": deadline})
    html = client.get("/goals").get_data(as_text=True)
    assert "Read books" in html and "25.0%" in html and "30 days left" in html
    client.post("/goals/1/progress", data={"amount": "3"})
    assert "50.0%" in client.get("/goals").get_data(as_text=True)


def test_goal_reaches_done(client):
    deadline = (date.today() + timedelta(days=5)).isoformat()
    client.post("/goals", data={"name": "Ship it", "target": "2", "deadline": deadline})
    client.post("/goals/1/progress", data={"amount": "5"})
    html = client.get("/goals").get_data(as_text=True)
    assert "100.0%" in html and "reached" in html


def test_invalid_goal_rejected(client):
    resp = client.post("/goals", data={"name": "", "target": "5", "deadline": "2030-01-01"}, follow_redirects=True)
    assert "positive target" in resp.get_data(as_text=True)


def test_delete_goal(client):
    deadline = (date.today() + timedelta(days=5)).isoformat()
    client.post("/goals", data={"name": "Temp goal", "target": "2", "deadline": deadline})
    client.post("/goals/1/delete")
    assert "Temp goal" not in client.get("/goals").get_data(as_text=True)


def test_seeded_goals_exist(seeded):
    assert "Run 100 km" in seeded.get("/goals").get_data(as_text=True)
