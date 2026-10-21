import json
from datetime import date


def test_health_returns_json(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok" and "version" in data


def test_dashboard_shows_seed_data_and_footer(client):
    html = client.get("/").get_data(as_text=True)
    assert "Drink 2L water" in html
    assert "Build" in html and "Backend pod" in html and "Commit" in html


def test_footer_reads_environment(client, monkeypatch):
    monkeypatch.setenv("BUILD_NUMBER", "42")
    monkeypatch.setenv("GIT_COMMIT", "abcdef1234")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    html = client.get("/").get_data(as_text=True)
    assert "#42" in html and "abcdef1" in html and "1.0.0" in html


def test_add_habit(client):
    client.post("/habits", data={"name": "Stretch"})
    assert "Stretch" in client.get("/habits").get_data(as_text=True)


def test_blank_habit_rejected(client):
    resp = client.post("/habits", data={"name": "  "}, follow_redirects=True)
    assert "Please give the habit a name" in resp.get_data(as_text=True)


def test_toggle_checkin_twice_restores_state(client):
    first = client.post("/habits/3/toggle", follow_redirects=True).get_data(as_text=True)
    assert "Done today" in first
    second = client.post("/habits/3/toggle", follow_redirects=True).get_data(as_text=True)
    assert "Check in today" in second


def test_add_expense_updates_category_total(client):
    client.post("/expenses", data={"amount": "12.5", "category": "Health", "day": date.today().isoformat()})
    assert "$12.50" in client.get("/expenses").get_data(as_text=True)


def test_invalid_expense_rejected(client):
    resp = client.post("/expenses", data={"amount": "-3", "category": "Food", "day": "2026-01-01"}, follow_redirects=True)
    assert "positive amount" in resp.get_data(as_text=True)


def test_set_budget_changes_percent(client):
    client.post("/expenses/budget", data={"budget": "1234"})
    html = client.get("/expenses").get_data(as_text=True)
    assert "$1234" in html


def test_footer_shows_frontend_pod_from_proxy_header(client):
    html = client.get("/", headers={"X-Frontend-Pod": "lifelog-frontend-abc"}).get_data(as_text=True)
    assert "lifelog-frontend-abc" in html


def test_delete_habit_and_expense(client):
    client.post("/habits/1/delete")
    assert "Drink 2L water" not in client.get("/habits").get_data(as_text=True)
    client.post("/expenses", data={"amount": "777.77", "category": "Food", "day": date.today().isoformat()})
    import sqlite3
    conn = sqlite3.connect(client.application.config["DATABASE"])
    new_id = conn.execute("SELECT id FROM expenses WHERE amount = 777.77").fetchone()[0]
    conn.close()
    client.post(f"/expenses/{new_id}/delete")
    assert "777.77" not in client.get("/expenses").get_data(as_text=True)


def test_dashboard_has_richer_sections(client):
    html = client.get("/").get_data(as_text=True)
    for text in ["Spending, last 14 days", "Goal progress", "Running on", "Budget left"]:
        assert text in html
