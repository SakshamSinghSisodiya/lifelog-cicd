import json
import re
import sqlite3


def test_health_json(client):
    data = json.loads(client.get("/health").data)
    assert data["status"] == "ok" and "version" in data


def test_footer_reads_environment(client, monkeypatch):
    monkeypatch.setenv("BUILD_NUMBER", "42")
    monkeypatch.setenv("GIT_COMMIT", "abcdef1234")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    monkeypatch.setenv("HOSTNAME", "pod-xyz")
    html = client.get("/").get_data(as_text=True)
    for text in ("#42", "abcdef1", "1.0.0", "pod-xyz"):
        assert text in html


def test_footer_defaults_to_dev(client, monkeypatch):
    for var in ("BUILD_NUMBER", "GIT_COMMIT", "APP_VERSION", "HOSTNAME"):
        monkeypatch.delenv(var, raising=False)
    assert "Build <strong>#dev" in client.get("/").get_data(as_text=True)


def test_footer_shows_frontend_pod_header(client):
    html = client.get("/", headers={"X-Frontend-Pod": "fe-123"}).get_data(as_text=True)
    assert "fe-123" in html


def test_empty_state_and_capture_bar_everywhere(client):
    assert "Nothing to track yet" in client.get("/").get_data(as_text=True)
    for url in ("/", "/log", "/insights", "/trackers"):
        assert 'id="cap-input"' in client.get(url).get_data(as_text=True)


def test_all_pages_render_with_seed_data(seeded):
    for url in ("/", "/log", "/insights", "/insights?range=7", "/insights?range=90", "/trackers", "/trackers/new", "/t/1", "/t/3", "/t/7", "/t/4/edit"):
        assert seeded.get(url).status_code == 200, url


def test_inline_controls_change_values(seeded):
    page = lambda: seeded.get("/").get_data(as_text=True)  # noqa: E731
    before = page()
    seeded.post("/t/3/log", data={"op": "inc"})
    seeded.post("/t/3/log", data={"op": "inc"})
    assert page() != before
    seeded.post("/t/4/log", data={"op": "set", "value": "6.5"})
    assert 'value="6.5"' in page()
    seeded.post("/t/6/log", data={"op": "mood", "value": "4"})
    assert re.search(r'name="value" value="4" class="on"', page())
    seeded.post("/t/6/log", data={"op": "mood", "value": "9"})  # out of range is ignored
    assert re.search(r'name="value" value="4" class="on"', page())


def test_toggle_check_twice(seeded):
    seeded.post("/t/2/log", data={"op": "toggle"})
    seeded.post("/t/2/log", data={"op": "toggle"})
    assert seeded.get("/").status_code == 200


def test_log_unknown_tracker_404(client):
    assert client.post("/t/99/log", data={"op": "toggle"}).status_code == 404


def test_past_day_view_and_future_clamped(seeded):
    assert "Viewing a past day" in seeded.get("/?d=2020-01-05").get_data(as_text=True)
    assert "Viewing a past day" not in seeded.get("/?d=2999-01-01").get_data(as_text=True)


def test_create_edit_archive_restore_tracker(client):
    client.post("/trackers/new?type=count", data={"name": "Pages", "color": "sky", "target": "30", "days": ["0", "1"]})
    page = client.get("/trackers").get_data(as_text=True)
    assert "Pages" in page and "target 30" in page
    client.post("/t/1/edit", data={"name": "Pages read", "color": "rose", "target": "40", "days": ["0"]})
    assert "Pages read" in client.get("/t/1").get_data(as_text=True)
    client.post("/t/1/archive")
    assert "Restore" in client.get("/trackers").get_data(as_text=True)
    client.post("/t/1/restore")
    assert "Restore" not in client.get("/trackers").get_data(as_text=True)


def test_tracker_form_validation(client):
    r = client.post("/trackers/new", data={"name": " ", "days": ["0"]}, follow_redirects=True)
    assert "Give the tracker a name" in r.get_data(as_text=True)
    r = client.post("/trackers/new", data={"name": "X"}, follow_redirects=True)
    assert "Pick at least one day" in r.get_data(as_text=True)
    r = client.post("/trackers/new", data={"name": "X", "days": ["0"], "target": "abc"})
    assert "Target must be a number" in r.get_data(as_text=True)


def test_delete_entry(seeded, app):
    conn = sqlite3.connect(seeded.application.config["DATABASE"])
    entry_id = conn.execute("SELECT id FROM entries WHERE tracker_id = 7 LIMIT 1").fetchone()[0]
    conn.close()
    seeded.post(f"/entries/{entry_id}/delete")
    conn = sqlite3.connect(seeded.application.config["DATABASE"])
    assert conn.execute("SELECT COUNT(*) FROM entries WHERE id = ?", (entry_id,)).fetchone()[0] == 0


def test_main_never_mentions_goals(seeded):
    assert seeded.get("/goals").status_code == 404
    for url in ("/", "/log", "/insights", "/trackers"):
        assert "goals" not in seeded.get(url).get_data(as_text=True).lower(), url
