"""Database operations for trackers and entries, and applying parsed capture intents."""
from datetime import date, datetime, timedelta

from .stats import is_met


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---- trackers -------------------------------------------------------------

def list_trackers(db, archived=False):
    rows = db.execute("SELECT * FROM trackers WHERE archived = ? ORDER BY position, id", (1 if archived else 0,))
    return [dict(r) for r in rows]


def get_tracker(db, tracker_id):
    row = db.execute("SELECT * FROM trackers WHERE id = ?", (tracker_id,)).fetchone()
    return dict(row) if row else None


def create_tracker(db, name, ttype, color="sage", unit="", target=None, days="0123456"):
    position = db.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM trackers").fetchone()[0]
    cur = db.execute(
        "INSERT INTO trackers (name, type, color, unit, target, days, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, ttype, color, unit, target, days, position),
    )
    db.commit()
    return cur.lastrowid


def update_tracker(db, tracker_id, name, color, unit, target, days):
    db.execute("UPDATE trackers SET name=?, color=?, unit=?, target=?, days=? WHERE id=?",
               (name, color, unit, target, days, tracker_id))
    db.commit()


def set_archived(db, tracker_id, archived):
    db.execute("UPDATE trackers SET archived = ? WHERE id = ?", (1 if archived else 0, tracker_id))
    db.commit()


# ---- reading entries ------------------------------------------------------

def day_values(db, day):
    rows = db.execute("SELECT tracker_id, SUM(value) AS v FROM entries WHERE day = ? GROUP BY tracker_id", (day.isoformat(),))
    return {r["tracker_id"]: r["v"] for r in rows}


def history(db, tracker_id, since, until=None):
    until = until or date.today()
    rows = db.execute(
        "SELECT day, SUM(value) AS v FROM entries WHERE tracker_id=? AND day BETWEEN ? AND ? GROUP BY day",
        (tracker_id, since.isoformat(), until.isoformat()),
    )
    return {date.fromisoformat(r["day"]): r["v"] for r in rows}


def tracker_entries(db, tracker_id, limit=15):
    return [dict(r) for r in db.execute(
        "SELECT * FROM entries WHERE tracker_id=? ORDER BY day DESC, id DESC LIMIT ?", (tracker_id, limit))]


def money_summary(db, today):
    month = today.strftime("%Y-%m")
    rows = db.execute(
        "SELECT e.day, e.value, e.category FROM entries e JOIN trackers t ON t.id = e.tracker_id "
        "WHERE t.type = 'money' AND t.archived = 0 AND e.day LIKE ?", (month + "%",)).fetchall()
    budget = db.execute("SELECT COALESCE(SUM(target), 0) FROM trackers WHERE type='money' AND archived=0").fetchone()[0]
    by_category: dict[str, float] = {}
    for r in rows:
        by_category[r["category"] or "Other"] = by_category.get(r["category"] or "Other", 0) + r["value"]
    spent = sum(by_category.values())
    return {
        "today": sum(r["value"] for r in rows if r["day"] == today.isoformat()),
        "month": spent,
        "budget": budget,
        "percent": round(spent / budget * 100) if budget else 0,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
    }


def feed(db, since):
    rows = db.execute(
        "SELECT e.*, t.name, t.type, t.color, t.unit, t.target FROM entries e JOIN trackers t ON t.id = e.tracker_id "
        "WHERE e.day >= ? ORDER BY e.day DESC, e.id DESC", (since.isoformat(),)).fetchall()
    return [dict(r) for r in rows]


def recent_actions(db, limit=6):
    return [r["label"] for r in db.execute("SELECT label FROM actions WHERE undone=0 ORDER BY id DESC LIMIT ?", (limit,))]


# ---- writing entries ------------------------------------------------------

def write_value(db, tracker_id, day, value, note=""):
    """Upsert the single entry of a non-money tracker. Returns the previous value (or None)."""
    row = db.execute("SELECT id, value FROM entries WHERE tracker_id=? AND day=?", (tracker_id, day.isoformat())).fetchone()
    if row:
        db.execute("UPDATE entries SET value=?, note=? WHERE id=?", (value, note, row["id"]))
        return row["value"]
    db.execute("INSERT INTO entries (tracker_id, day, value, note, created_at) VALUES (?, ?, ?, ?, ?)",
               (tracker_id, day.isoformat(), value, note, _now()))
    return None


def write_money(db, tracker_id, day, amount, category, note=""):
    cur = db.execute("INSERT INTO entries (tracker_id, day, value, category, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                     (tracker_id, day.isoformat(), amount, category, note, _now()))
    return cur.lastrowid


def delete_entry(db, entry_id):
    db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    db.commit()


def log_inline(db, tracker, day, op, value):
    """Buttons on the Today page: toggle, inc, dec, set, mood."""
    current = day_values(db, day).get(tracker["id"])
    if op == "toggle":
        new = 0.0 if is_met("check", None, current) else 1.0
    elif op in ("inc", "dec"):
        new = max((current or 0) + (1 if op == "inc" else -1), 0)
    else:
        new = value
    if new is None:
        return
    write_value(db, tracker["id"], day, new)
    db.commit()


# ---- capture intents ------------------------------------------------------

def _new_value(intent, prev):
    return intent.value if intent.kind == "set" else max((prev or 0) + intent.value, 0)


def _when(day, today):
    delta = (today - day).days
    return "today" if delta == 0 else "yesterday" if delta == 1 else day.strftime("%a %d %b")


def num(v):
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def describe(db, intent, today, currency):
    """Human sentence for what the intent will do (used by preview and as the action label)."""
    t, when = intent.tracker, _when(intent.day, today)
    if intent.kind == "money":
        return f"Spend {currency}{num(intent.value)} · {intent.category}" + (f" · {intent.note}" if intent.note else "") + f" · {when}"
    prev = day_values(db, intent.day).get(t["id"])
    new = _new_value(intent, prev)
    if t["type"] == "check":
        return f"{t['name']} {'done' if new else 'not done'} · {when}"
    target = f"/{num(t['target'])}" if t["target"] and t["type"] == "count" else ""
    unit = f" {t['unit']}" if t["unit"] else ""
    sign = "+" if intent.kind == "add" and intent.value >= 0 else ""
    verb = f"{sign}{num(intent.value)} → " if intent.kind == "add" else "→ "
    return f"{t['name']} {verb}{num(new)}{target}{unit} · {when}"


def apply_intent(db, intent, today, currency):
    message = describe(db, intent, today, currency)
    t = intent.tracker
    if intent.kind == "money":
        entry_id = write_money(db, t["id"], intent.day, intent.value, intent.category, intent.note)
        db.execute("INSERT INTO actions (kind, tracker_id, day, entry_id, label) VALUES ('money', ?, ?, ?, ?)",
                   (t["id"], intent.day.isoformat(), entry_id, message))
    else:
        prev = write_value(db, t["id"], intent.day, _new_value(intent, day_values(db, intent.day).get(t["id"])), intent.note)
        db.execute("INSERT INTO actions (kind, tracker_id, day, prev_value, label) VALUES ('set', ?, ?, ?, ?)",
                   (t["id"], intent.day.isoformat(), prev, message))
    db.commit()
    return message


def create_from_capture(db, name, ttype):
    tracker_id = create_tracker(db, name, ttype, color=_next_color(db), unit="", target=1 if ttype == "check" else None)
    db.execute("INSERT INTO actions (kind, tracker_id, label) VALUES ('create', ?, ?)", (tracker_id, f"Created tracker {name}"))
    db.commit()
    return get_tracker(db, tracker_id)


def _next_color(db):
    from .stats import TONES

    return TONES[db.execute("SELECT COUNT(*) FROM trackers").fetchone()[0] % len(TONES)]


def undo_last(db):
    action = db.execute("SELECT * FROM actions WHERE undone = 0 ORDER BY id DESC LIMIT 1").fetchone()
    if not action:
        return None
    if action["kind"] == "money":
        db.execute("DELETE FROM entries WHERE id = ?", (action["entry_id"],))
    elif action["kind"] == "set":
        if action["prev_value"] is None:
            db.execute("DELETE FROM entries WHERE tracker_id=? AND day=?", (action["tracker_id"], action["day"]))
        else:
            db.execute("UPDATE entries SET value=? WHERE tracker_id=? AND day=?",
                       (action["prev_value"], action["tracker_id"], action["day"]))
    elif action["kind"] == "create":
        used = db.execute("SELECT COUNT(*) FROM entries WHERE tracker_id=?", (action["tracker_id"],)).fetchone()[0]
        if used:
            db.execute("UPDATE trackers SET archived = 1 WHERE id = ?", (action["tracker_id"],))
        else:
            db.execute("DELETE FROM trackers WHERE id = ?", (action["tracker_id"],))
    db.execute("UPDATE actions SET undone = 1 WHERE id = ?", (action["id"],))
    db.commit()
    return f"Undid: {action['label']}"


def entry_text(row, currency):
    """One line for the log feed."""
    if row["type"] == "money":
        extra = " · ".join(x for x in (row["category"], row["note"]) if x)
        return f"{currency}{num(row['value'])}" + (f" · {extra}" if extra else "")
    if row["type"] == "check":
        return "done" if row["value"] else "not done"
    target = f"/{num(row['target'])}" if row["target"] and row["type"] == "count" else ""
    unit = f" {row['unit']}" if row["unit"] else ""
    return f"{num(row['value'])}{target}{unit}" + (" · " + row["note"] if row["note"] else "")


def days_back(n, today=None):
    return (today or date.today()) - timedelta(days=n)


def parse_day(value, today):
    """?d=YYYY-MM-DD, never in the future."""
    try:
        day = date.fromisoformat(value or "")
    except ValueError:
        return today
    return min(day, today)
