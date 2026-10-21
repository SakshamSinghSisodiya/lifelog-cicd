import os
from datetime import date, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from . import expenses_logic as ex
from . import goals_logic as gl
from . import habits_logic as hl
from . import insights as ins
from .db import get_db

bp = Blueprint("main", __name__)
CATEGORIES = ["Food", "Transport", "Home", "Fun", "Health", "Other"]


def habit_rows(today):
    db = get_db()
    rows = []
    for habit in db.execute("SELECT id, name FROM habits ORDER BY id"):
        days = hl.parse_days(
            r["day"] for r in db.execute("SELECT day FROM checkins WHERE habit_id = ?", (habit["id"],))
        )
        rows.append(
            {
                "id": habit["id"],
                "name": habit["name"],
                "done_today": today in days,
                "current": hl.current_streak(days, today),
                "longest": hl.longest_streak(days),
                "week": ins.week_flags(days, today),
                "rate": ins.completion_rate(days, today),
            }
        )
    return rows


def month_summary(month):
    db = get_db()
    expenses = db.execute("SELECT amount, category, day FROM expenses WHERE day LIKE ?", (month + "%",)).fetchall()
    totals = ex.totals_by_category(expenses, month)
    spent = round(sum(totals.values()), 2)
    row = db.execute("SELECT amount FROM budgets WHERE month = ?", (month,)).fetchone()
    budget = row["amount"] if row else 0.0
    percent = ex.percent_used(spent, budget)
    return {
        "month": month,
        "totals": totals,
        "shares": ins.category_shares(totals),
        "spent": spent,
        "budget": budget,
        "left": round(budget - spent, 2),
        "percent": percent,
        "bar": min(percent, 100),
        "status": ex.budget_status(percent),
    }


def spend_chart(today, n=14):
    since = (today - timedelta(days=n - 1)).isoformat()
    rows = get_db().execute("SELECT amount, day FROM expenses WHERE day >= ?", (since,)).fetchall()
    daily = ins.daily_totals(rows, today, n)
    top = max((v for _, v in daily), default=0) or 1
    return [{"day": d, "value": v, "height": round(v / top * 100)} for d, v in daily], round(sum(v for _, v in daily), 2)


@bp.route("/")
def dashboard():
    today = date.today()
    habits = habit_rows(today)
    done = sum(1 for h in habits if h["done_today"])
    summary = month_summary(today.strftime("%Y-%m"))
    chart, chart_total = spend_chart(today)
    goals = [
        {**dict(g), "percent": gl.percent_complete(g["progress"], g["target"])}
        for g in get_db().execute("SELECT * FROM goals ORDER BY deadline LIMIT 3")
    ]
    recent = get_db().execute("SELECT * FROM expenses ORDER BY day DESC, id DESC LIMIT 5").fetchall()
    return render_template(
        "dashboard.html",
        habits=habits,
        done=done,
        pct=round(done / len(habits) * 100) if habits else 0,
        best=max(habits, key=lambda h: h["current"], default=None),
        summary=summary,
        projected=ins.projected_spend(summary["spent"], today),
        chart=chart,
        chart_total=chart_total,
        goals=goals,
        recent=recent,
        quote=ins.quote_for(today),
        today=today,
    )


@bp.route("/habits", methods=["GET", "POST"])
def habits():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            db = get_db()
            db.execute("INSERT INTO habits (name) VALUES (?)", (name[:60],))
            db.commit()
        else:
            flash("Please give the habit a name.")
        return redirect(url_for("main.habits"))
    return render_template("habits.html", habits=habit_rows(date.today()))


@bp.route("/habits/<int:habit_id>/delete", methods=["POST"])
def delete_habit(habit_id):
    db = get_db()
    db.execute("DELETE FROM checkins WHERE habit_id = ?", (habit_id,))
    db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    db.commit()
    return redirect(url_for("main.habits"))


@bp.route("/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle(habit_id):
    db = get_db()
    day = date.today().isoformat()
    if db.execute("SELECT 1 FROM checkins WHERE habit_id=? AND day=?", (habit_id, day)).fetchone():
        db.execute("DELETE FROM checkins WHERE habit_id=? AND day=?", (habit_id, day))
    elif db.execute("SELECT 1 FROM habits WHERE id=?", (habit_id,)).fetchone():
        db.execute("INSERT INTO checkins VALUES (?, ?)", (habit_id, day))
    db.commit()
    return redirect(request.form.get("next") or url_for("main.habits"))


@bp.route("/expenses", methods=["GET", "POST"])
def expenses():
    db = get_db()
    if request.method == "POST":
        try:
            amount = float(request.form.get("amount", ""))
            day = date.fromisoformat(request.form.get("day", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a positive amount and a valid date.")
            return redirect(url_for("main.expenses"))
        category = request.form.get("category", "Other")
        db.execute(
            "INSERT INTO expenses (amount, category, day) VALUES (?, ?, ?)",
            (amount, category if category in CATEGORIES else "Other", day.isoformat()),
        )
        db.commit()
        return redirect(url_for("main.expenses"))
    today = date.today()
    recent = db.execute("SELECT * FROM expenses ORDER BY day DESC, id DESC LIMIT 12").fetchall()
    summary = month_summary(today.strftime("%Y-%m"))
    chart, chart_total = spend_chart(today)
    return render_template(
        "expenses.html",
        summary=summary,
        projected=ins.projected_spend(summary["spent"], today),
        chart=chart,
        chart_total=chart_total,
        recent=recent,
        categories=CATEGORIES,
        today=date.today().isoformat(),
    )


@bp.route("/expenses/<int:expense_id>/delete", methods=["POST"])
def delete_expense(expense_id):
    db = get_db()
    db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    db.commit()
    return redirect(url_for("main.expenses"))


@bp.route("/expenses/budget", methods=["POST"])
def set_budget():
    try:
        amount = float(request.form.get("budget", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Budget must be a positive number.")
        return redirect(url_for("main.expenses"))
    db = get_db()
    db.execute(
        "INSERT INTO budgets (month, amount) VALUES (?, ?) ON CONFLICT(month) DO UPDATE SET amount=excluded.amount",
        (date.today().strftime("%Y-%m"), amount),
    )
    db.commit()
    return redirect(url_for("main.expenses"))


@bp.route("/health")
def health():
    return jsonify(status="ok", version=os.environ.get("APP_VERSION", "dev"))
