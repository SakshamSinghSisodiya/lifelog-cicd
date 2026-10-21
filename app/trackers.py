from datetime import date, timedelta
from statistics import mean

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from . import service, stats
from .db import get_db

bp = Blueprint("trackers", __name__)
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_form(form, ttype):
    name = form.get("name", "").strip()[:40]
    days = "".join(sorted(d for d in form.getlist("days") if d in "0123456" and len(d) == 1))
    if not name:
        return None, "Give the tracker a name."
    if not days:
        return None, "Pick at least one day."
    try:
        target = float(form["target"]) if form.get("target", "").strip() else None
    except ValueError:
        return None, "Target must be a number."
    if target is not None and target <= 0:
        return None, "Target must be above zero."
    color = form.get("color") if form.get("color") in stats.TONES else "sage"
    return {"name": name, "color": color, "unit": form.get("unit", "").strip()[:12], "target": target, "days": days}, None


@bp.route("/trackers")
def manage():
    db = get_db()
    return render_template("trackers.html", active=service.list_trackers(db), archived=service.list_trackers(db, True))


@bp.route("/trackers/new", methods=["GET", "POST"])
def new():
    ttype = request.values.get("type", "check")
    if ttype not in stats.TYPES:
        ttype = "check"
    if request.method == "POST":
        data, error = parse_form(request.form, ttype)
        if error:
            flash(error)
        else:
            service.create_tracker(get_db(), data["name"], ttype, data["color"], data["unit"], data["target"], data["days"])
            return redirect(url_for("trackers.manage"))
    return render_template("tracker_form.html", tracker=None, ttype=ttype, tones=stats.TONES, day_names=DAY_NAMES, types=stats.TYPES)


@bp.route("/t/<int:tracker_id>/edit", methods=["GET", "POST"])
def edit(tracker_id):
    db = get_db()
    tracker = service.get_tracker(db, tracker_id) or abort(404)
    if request.method == "POST":
        data, error = parse_form(request.form, tracker["type"])
        if error:
            flash(error)
        else:
            service.update_tracker(db, tracker_id, data["name"], data["color"], data["unit"], data["target"], data["days"])
            return redirect(url_for("trackers.detail", tracker_id=tracker_id))
    return render_template("tracker_form.html", tracker=tracker, ttype=tracker["type"], tones=stats.TONES, day_names=DAY_NAMES, types=stats.TYPES)


@bp.route("/t/<int:tracker_id>/<action>", methods=["POST"])
def archive(tracker_id, action):
    if action not in ("archive", "restore") or not service.get_tracker(get_db(), tracker_id):
        abort(404)
    service.set_archived(get_db(), tracker_id, action == "archive")
    return redirect(url_for("trackers.manage"))


@bp.route("/entries/<int:entry_id>/delete", methods=["POST"])
def delete_entry(entry_id):
    service.delete_entry(get_db(), entry_id)
    return redirect(request.form.get("next") or url_for("main.today"))


def heat_grid(ttype, target, days, hist, today, weeks=12):
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    grid = []
    for w in range(weeks):
        column = []
        for d in range(7):
            day = start + timedelta(weeks=w, days=d)
            if day > today:
                column.append({"day": day, "state": "future"})
            else:
                column.append(stats.cells(ttype, target, days, hist, day, 1)[0])
        grid.append(column)
    return grid


@bp.route("/t/<int:tracker_id>")
def detail(tracker_id):
    db, today = get_db(), date.today()
    t = service.get_tracker(db, tracker_id) or abort(404)
    hist = service.history(db, tracker_id, today - timedelta(days=400), today)
    current, best = stats.streaks(t["type"], t["target"], t["days"], hist, today)
    recent = [v for d, v in hist.items() if d > today - timedelta(days=30)]
    facts = {
        "current": current, "best": best,
        "rate": stats.completion_rate(t["type"], t["target"], t["days"], hist, today),
        "logged": len([d for d in hist if d > today - timedelta(days=30)]),
        "avg": round(mean(recent), 1) if recent else None,
        "low": min(recent) if recent else None, "high": max(recent) if recent else None,
        "latest": hist[max(hist)] if hist else None,
    }
    money = service.money_summary(db, today) if t["type"] == "money" else None
    return render_template(
        "tracker_detail.html", t=t, facts=facts, money=money, day_names=DAY_NAMES,
        grid=heat_grid(t["type"], t["target"], t["days"], hist, today),
        entries=[{**e, "text": service.entry_text({**t, **e}, current_app.config["CURRENCY"])} for e in service.tracker_entries(db, tracker_id)],
    )
