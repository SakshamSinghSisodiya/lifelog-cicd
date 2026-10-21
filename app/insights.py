from datetime import date, timedelta
from statistics import mean

from flask import Blueprint, render_template, request

from . import service, stats
from .db import get_db

bp = Blueprint("insights", __name__)
RANGES = (7, 30, 90)


def money_series(db, tracker_id, since, today, n):
    rows = db.execute(
        "SELECT day, category, SUM(value) AS v FROM entries WHERE tracker_id=? AND day BETWEEN ? AND ? GROUP BY day, category",
        (tracker_id, since.isoformat(), today.isoformat())).fetchall()
    daily: dict[str, float] = {}
    by_category: dict[str, float] = {}
    for r in rows:
        daily[r["day"]] = daily.get(r["day"], 0) + r["v"]
        by_category[r["category"] or "Other"] = by_category.get(r["category"] or "Other", 0) + r["v"]
    days = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
    values = [daily.get(d.isoformat(), 0) for d in days]
    top = max(values) or 1
    bars = [{"day": d, "value": v, "height": round(v / top * 100)} for d, v in zip(days, values)]
    total = sum(values)
    return {
        "bars": bars, "total": total, "avg": round(total / n),
        "by_category": [{"name": k, "amount": v, "percent": round(v / total * 100)} for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])] if total else [],
    }


@bp.route("/insights")
def view():
    db, today = get_db(), date.today()
    n = int(request.args.get("range", 30)) if request.args.get("range", "30").isdigit() else 30
    n = n if n in RANGES else 30
    since = today - timedelta(days=n - 1)
    sections, rates = [], []
    for t in service.list_trackers(db):
        hist = service.history(db, t["id"], today - timedelta(days=400), today)
        window = {d: v for d, v in hist.items() if d >= since}
        current, best = stats.streaks(t["type"], t["target"], t["days"], hist, today)
        sec = {"t": t, "current": current, "best": best, "logged": len(window),
               "rate": stats.completion_rate(t["type"], t["target"], t["days"], hist, today, n),
               "cells": stats.cells(t["type"], t["target"], t["days"], hist, today, n)}
        if t["type"] in ("number", "mood"):
            series = [hist.get(today - timedelta(days=i)) for i in range(n - 1, -1, -1)]
            sec.update(spark=stats.sparkline(series), avg=round(mean(window.values()), 1) if window else None,
                       low=min(window.values()) if window else None, high=max(window.values()) if window else None)
        if t["type"] == "money":
            sec["money"] = money_series(db, t["id"], since, today, n)
        if t["type"] in ("check", "count"):
            rates.append(sec["rate"])
        sections.append(sec)
    overall = round(mean(rates)) if rates else 0
    return render_template("insights.html", sections=sections, n=n, ranges=RANGES, overall=overall, since=since)
