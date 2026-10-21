from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from . import goals_logic as gl
from .db import get_db

bp = Blueprint("goals", __name__)


def goal_rows(db, today):
    rows = []
    for row in db.execute("SELECT * FROM goals ORDER BY deadline, id"):
        deadline = date.fromisoformat(row["deadline"])
        rows.append({
            **dict(row),
            "percent": gl.percent_complete(row["progress"], row["target"]),
            "days_left": gl.days_left(deadline, today),
            "status": gl.goal_status(row["progress"], row["target"], deadline, today),
        })
    return rows


@bp.route("/goals", methods=["GET", "POST"])
def goals():
    db = get_db()
    if request.method == "POST":
        try:
            name = request.form.get("name", "").strip()
            target = float(request.form.get("target", ""))
            progress = float(request.form.get("progress") or 0)
            deadline = date.fromisoformat(request.form.get("deadline", ""))
            if not name or target <= 0 or progress < 0:
                raise ValueError
        except ValueError:
            flash("Give the goal a name, a positive target, a valid deadline and a progress of 0 or more.")
            return redirect(url_for("goals.goals"))
        db.execute("INSERT INTO goals (name, target, progress, deadline) VALUES (?, ?, ?, ?)",
                   (name[:60], target, progress, deadline.isoformat()))
        db.commit()
        return redirect(url_for("goals.goals"))
    today = date.today()
    return render_template("goals.html", goals=goal_rows(db, today), today=today.isoformat())


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


@bp.route("/goals/<int:goal_id>/delete", methods=["POST"])
def delete_goal(goal_id):
    db = get_db()
    db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    db.commit()
    return redirect(url_for("goals.goals"))
