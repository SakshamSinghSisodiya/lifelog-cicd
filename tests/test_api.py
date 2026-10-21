import sqlite3
from datetime import date


def post(client, url, **body):
    return client.post(url, json=body).get_json()


def add(app, name, ttype, target=None):
    from app import service
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    tid = service.create_tracker(conn, name, ttype, target=target)
    conn.close()
    return tid


def values(app, tid):
    conn = sqlite3.connect(app.config["DATABASE"])
    rows = conn.execute("SELECT day, value FROM entries WHERE tracker_id=?", (tid,)).fetchall()
    conn.close()
    return rows


def test_preview_describes_without_writing(app, client):
    tid = add(app, "Water", "count", 8)
    data = post(client, "/api/capture/preview", text="water 3")
    assert data["status"] == "add" and "Water +3 → 3/8" in data["preview"]
    assert values(app, tid) == []


def test_capture_applies_and_accumulates(app, client):
    tid = add(app, "Water", "count", 8)
    post(client, "/api/capture", text="water 3")
    data = post(client, "/api/capture", text="water 2")
    assert data["ok"] and "→ 5/8" in data["message"] and data["preview"] == ""
    assert [v for _, v in values(app, tid)] == [5.0]


def test_check_set_money_and_backfill(app, client):
    gym = add(app, "Gym", "check")
    spend = add(app, "Spending", "money")
    post(client, "/api/capture", text="yesterday gym")
    post(client, "/api/capture", text="spent 250 lunch")
    assert values(app, gym)[0][0] != date.today().isoformat()
    assert [v for _, v in values(app, spend)] == [250.0]


def test_undo_reverses_last_action(app, client):
    tid = add(app, "Water", "count", 8)
    post(client, "/api/capture", text="water 3")
    post(client, "/api/capture", text="water 2")
    assert post(client, "/api/capture", text="undo")["ok"]
    assert [v for _, v in values(app, tid)] == [3.0]
    post(client, "/api/capture", text="undo")
    assert values(app, tid) == []
    assert post(client, "/api/capture", text="undo")["ok"] is False


def test_undo_money_deletes_the_entry(app, client):
    spend = add(app, "Spending", "money")
    post(client, "/api/capture", text="spent 90 uber")
    post(client, "/api/capture", text="undo")
    assert values(app, spend) == []


def test_unknown_tracker_offers_create_then_logs(app, client):
    data = post(client, "/api/capture", text="pushups 20")
    assert data["ok"] is False and data["create"]["name"] == "Pushups"
    created = post(client, "/api/capture", text="pushups 20", create=data["create"])
    assert created["ok"] and "Pushups +20" in created["message"]


def test_undo_of_created_tracker_removes_it(app, client):
    post(client, "/api/capture", text="yoga", create={"name": "Yoga", "type": "check"})
    post(client, "/api/capture", text="undo")  # undo the log
    post(client, "/api/capture", text="undo")  # undo the creation
    assert "Yoga" not in client.get("/trackers").get_data(as_text=True)


def test_ambiguous_returns_suggestions(app, client):
    add(app, "Read", "check")
    add(app, "Reflect", "check")
    data = post(client, "/api/capture", text="re")
    assert data["status"] == "ambiguous" and len(data["suggestions"]) == 2


def test_invalid_create_type_is_ignored(app, client):
    data = post(client, "/api/capture", text="x y", create={"name": "Bad", "type": "nope"})
    assert data["ok"] is False


def test_empty_text(client):
    assert post(client, "/api/capture/preview", text="")["status"] == "empty"
