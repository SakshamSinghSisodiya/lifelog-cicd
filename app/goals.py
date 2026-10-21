from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import goals_logic as gl
from .db import get_db

bp = Blueprint("goals", __name__)


@bp.route("/goals", methods=["GET", "POST"])
def goals():
    db = get_db()
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            target = float(request.form.get("target", ""))
            deadline = date.fromisoformat(request.form.get("deadline", ""))
            if not name or target <= 0:
                raise ValueError
        except ValueError:
            flash("Give the goal a name, a positive target and a deadline.")
            return redirect(url_for("goals.goals"))
        db.execute(
            "INSERT INTO goals (name, target, progress, deadline) VALUES (?, ?, 0, ?)",
            (name[:60], target, deadline.isoformat()),
        )
        db.commit()
        return redirect(url_for("goals.goals"))

    today = date.today()
    items = []
    for row in db.execute("SELECT * FROM goals ORDER BY deadline"):
        deadline = date.fromisoformat(row["deadline"])
        percent = gl.percent_complete(row["progress"], row["target"])
        items.append(
            {
                **dict(row),
                "percent": percent,
                "days_left": gl.days_left(deadline, today),
                "status": gl.goal_status(row["progress"], row["target"], deadline, today),
            }
        )
    return render_template("goals.html", goals=items, today=today.isoformat())


@bp.route("/goals/<int:goal_id>/progress", methods=["POST"])
def add_progress(goal_id):
    try:
        amount = float(request.form.get("amount", ""))
    except ValueError:
        flash("Progress must be a number.")
        return redirect(url_for("goals.goals"))
    db = get_db()
    db.execute("UPDATE goals SET progress = MAX(progress + ?, 0) WHERE id = ?", (amount, goal_id))
    db.commit()
    return redirect(url_for("goals.goals"))
