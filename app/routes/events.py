import json
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.models.event import Event
from app.models.url import Url
from app.models.user import User

events_bp = Blueprint("events", __name__)


def _event_to_dict(event):
    """Convert an Event model to a dict with url_id and user_id."""
    d = model_to_dict(event, backrefs=False)
    d["url_id"] = event.url_id
    d["user_id"] = event.user_id
    if "url" in d:
        del d["url"]
    if "user" in d:
        del d["user"]
    # Parse details string to dict if it's JSON
    if isinstance(d.get("details"), str):
        try:
            d["details"] = json.loads(d["details"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


@events_bp.route("/events", methods=["GET", "POST"])
def list_or_create_events():
    if request.method == "POST":
        data = request.get_json(silent=True)
        if not data:
            return jsonify(error="Request body must be JSON", code="VALIDATION_ERROR"), 400

        missing = [f for f in ("url_id", "user_id", "event_type") if f not in data]
        if missing:
            return jsonify(error=f"Missing required fields: {', '.join(missing)}", code="VALIDATION_ERROR"), 400

        # Validate url exists
        try:
            Url.get_by_id(data["url_id"])
        except Url.DoesNotExist:
            return jsonify(error="URL not found", code="VALIDATION_ERROR"), 400

        # Validate user exists
        try:
            User.get_by_id(data["user_id"])
        except User.DoesNotExist:
            return jsonify(error="User not found", code="VALIDATION_ERROR"), 400

        details = data.get("details", {})
        if isinstance(details, dict):
            details = json.dumps(details)

        event = Event.create(
            url=data["url_id"],
            user=data["user_id"],
            event_type=data["event_type"],
            timestamp=datetime.now(timezone.utc),
            details=details,
        )
        return jsonify(_event_to_dict(event)), 201

    # GET — list events with filters
    query = Event.select()

    url_id = request.args.get("url_id")
    if url_id is not None:
        query = query.where(Event.url == int(url_id))

    user_id = request.args.get("user_id")
    if user_id is not None:
        query = query.where(Event.user == int(user_id))

    event_type = request.args.get("event_type")
    if event_type is not None:
        query = query.where(Event.event_type == event_type)

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    query = query.order_by(Event.id).paginate(page, per_page)

    results = [_event_to_dict(e) for e in query]
    return jsonify(results)
