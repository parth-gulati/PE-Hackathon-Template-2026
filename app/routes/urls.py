from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app import limiter
from app.auth import require_api_key
from app.utils import generate_short_code, is_valid_url

urls_bp = Blueprint("urls", __name__)

MAX_SHORT_CODE_RETRIES = 10


@urls_bp.route("/shorten", methods=["POST"])
@limiter.limit("30/minute")
@require_api_key
def create_short_url():
    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="Request body must be JSON", code="VALIDATION_ERROR"), 400

    # Validate required fields
    missing = [f for f in ("original_url", "title", "user_id") if f not in data]
    if missing:
        return (
            jsonify(
                error=f"Missing required fields: {', '.join(missing)}",
                code="VALIDATION_ERROR",
            ),
            400,
        )

    # Validate URL format
    if not is_valid_url(data["original_url"]):
        return jsonify(error="Invalid URL format", code="VALIDATION_ERROR"), 400

    # Validate user exists
    try:
        user = User.get_by_id(data["user_id"])
    except User.DoesNotExist:
        return jsonify(error="User not found", code="VALIDATION_ERROR"), 400

    # Generate unique short code with retry
    now = datetime.now(timezone.utc)
    for _ in range(MAX_SHORT_CODE_RETRIES):
        short_code = generate_short_code()
        try:
            with db.atomic():
                url = Url.create(
                    user=user,
                    short_code=short_code,
                    original_url=data["original_url"],
                    title=data["title"],
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
                Event.create(
                    url=url,
                    user=user,
                    event_type="created",
                    timestamp=now,
                    details=f'{{"short_code":"{short_code}","original_url":"{data["original_url"]}"}}',
                )
            result = model_to_dict(url, backrefs=False)
            result["user_id"] = user.id
            if "user" in result:
                del result["user"]
            return jsonify(result), 201
        except Exception:
            continue

    return jsonify(error="Failed to generate unique short code", code="INTERNAL_ERROR"), 500


@urls_bp.route("/urls")
def list_urls():
    query = Url.select()

    user_id = request.args.get("user_id")
    if user_id is not None:
        query = query.where(Url.user == int(user_id))

    is_active = request.args.get("is_active")
    if is_active is not None:
        query = query.where(Url.is_active == (is_active.lower() == "true"))

    results = []
    for u in query:
        d = model_to_dict(u, backrefs=False)
        d["user_id"] = u.user_id
        if "user" in d:
            del d["user"]
        results.append(d)
    return jsonify(results)


@urls_bp.route("/urls/<int:url_id>")
def get_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify(error="URL not found", code="NOT_FOUND"), 404

    result = model_to_dict(url, backrefs=False)
    result["user_id"] = url.user_id
    if "user" in result:
        del result["user"]
    result["event_count"] = Event.select().where(Event.url == url).count()
    return jsonify(result)
