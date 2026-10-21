from datetime import date

from flask import Blueprint, current_app, jsonify, request

from . import service
from .capture import parse
from .db import get_db
from .stats import TYPES

bp = Blueprint("api", __name__, url_prefix="/api")


def _body():
    data = request.get_json(silent=True) or {}
    return str(data.get("text", ""))[:200], data.get("create")


def _payload(db, intent, today, extra=None):
    out = {"status": intent.kind, "message": intent.message, "preview": "", "suggestions": intent.suggestions, "create": None}
    if intent.kind in ("set", "add", "money"):
        out["preview"] = service.describe(db, intent, today, current_app.config["CURRENCY"])
    elif intent.kind == "undo":
        last = service.recent_actions(db, 1)
        out["preview"] = f"Undo: {last[0]}" if last else ""
        out["message"] = "" if last else "Nothing to undo."
    if intent.create:
        out["create"] = {**intent.create, "label": f"Create tracker '{intent.create['name']}' ({intent.create['type']})"}
    return {**out, **(extra or {})}


@bp.post("/capture/preview")
def preview():
    text, _ = _body()
    db, today = get_db(), date.today()
    return jsonify(_payload(db, parse(text, service.list_trackers(db), today), today))


@bp.post("/capture")
def capture():
    text, create = _body()
    db, today = get_db(), date.today()
    if isinstance(create, dict) and create.get("type") in TYPES and str(create.get("name", "")).strip():
        service.create_from_capture(db, str(create["name"]).strip()[:40], create["type"])
    intent = parse(text, service.list_trackers(db), today)
    if intent.kind == "undo":
        message = service.undo_last(db)
        return jsonify(_payload(db, intent, today, {"ok": message is not None, "message": message or "Nothing to undo."}))
    if intent.kind in ("set", "add", "money"):
        message = service.apply_intent(db, intent, today, current_app.config["CURRENCY"])
        return jsonify(_payload(db, intent, today, {"ok": True, "message": message}))
    return jsonify(_payload(db, intent, today, {"ok": False}))
