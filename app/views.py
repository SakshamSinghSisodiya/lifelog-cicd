import os
from datetime import date, timedelta

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

from . import service, stats
from .db import get_db

bp = Blueprint("main", __name__)


def tracker_rows(db, day, trackers):
    values = service.day_values(db, day)
    rows = []
    for t in trackers:
        hist = service.history(db, t["id"], day - timedelta(days=400), day)
        value = values.get(t["id"])
        met = stats.is_met(t["type"], t["target"], value)
        current, _best = stats.streaks(t["type"], t["target"], t["days"], hist, day)
        pct = min(round((value or 0) / t["target"] * 100), 100) if t["type"] == "count" and t["target"] else (100 if met else 0)
        rows.append({
            **t, "value": value, "met": met, "streak": current, "pct": pct,
            "scheduled": stats.is_scheduled(t["days"], day),
            "week": stats.cells(t["type"], t["target"], t["days"], hist, day, 7),
        })
    return rows


@bp.route("/")
def today():
    db, real_today = get_db(), date.today()
    day = service.parse_day(request.args.get("d"), real_today)
    rows = tracker_rows(db, day, service.list_trackers(db))
    countable = [r for r in rows if r["scheduled"] and r["type"] != "money"]
    done = sum(r["met"] for r in countable)
    return render_template(
        "today.html", day=day, is_today=day == real_today,
        prev_day=day - timedelta(days=1), next_day=day + timedelta(days=1) if day < real_today else None,
        due=[r for r in rows if r["scheduled"]], off=[r for r in rows if not r["scheduled"]],
        done=done, total=len(countable), pct=round(done / len(countable) * 100) if countable else 0,
        money=service.money_summary(db, real_today), recent=service.recent_actions(db),
        has_trackers=bool(rows),
    )


@bp.route("/t/<int:tracker_id>/log", methods=["POST"])
def log_inline(tracker_id):
    db = get_db()
    tracker = service.get_tracker(db, tracker_id)
    if not tracker:
        abort(404)
    day = service.parse_day(request.form.get("d"), date.today())
    try:
        value = float(request.form["value"]) if request.form.get("value", "") != "" else None
    except ValueError:
        value = None
    if tracker["type"] == "mood" and value is not None and not 1 <= value <= 5:
        value = None
    service.log_inline(db, tracker, day, request.form.get("op", "set"), value)
    return redirect(url_for("main.today", d=day.isoformat() if day != date.today() else None))


@bp.route("/log")
def log():
    db, today = get_db(), date.today()
    currency = os.environ.get("CURRENCY", "₹")
    groups: dict[str, list] = {}
    for row in service.feed(db, today - timedelta(days=13)):
        row["text"] = service.entry_text(row, currency)
        groups.setdefault(row["day"], []).append(row)
    days = [(date.fromisoformat(d), rows) for d, rows in groups.items()]
    return render_template("log.html", days=days, today=today)


@bp.route("/health")
def health():
    return jsonify(status="ok", version=os.environ.get("APP_VERSION", "dev"))
