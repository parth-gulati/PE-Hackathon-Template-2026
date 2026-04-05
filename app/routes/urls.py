from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict

from app.cache import cache_delete
from app.database import db
from app.models.event import Event
from app.models.url import Url
from app.models.user import User
from app import limiter
from app.utils import generate_short_code, is_valid_url

urls_bp = Blueprint("urls", __name__)

MAX_SHORT_CODE_RETRIES = 10


def _url_to_dict(url):
    """Convert a Url model to a dict with user_id instead of nested user."""
    d = model_to_dict(url, backrefs=False)
    d["user_id"] = url.user_id
    if "user" in d:
        del d["user"]
    return d


def _create_url(data):
    """Shared URL creation logic for both POST /shorten and POST /urls."""
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
            result = _url_to_dict(url)
            return jsonify(result), 201
        except Exception:
            continue

    return jsonify(error="Failed to generate unique short code", code="INTERNAL_ERROR"), 500


@urls_bp.route("/shorten", methods=["POST"])
@limiter.limit("500/minute")
def create_short_url():
    data = request.get_json(silent=True)
    return _create_url(data)


@urls_bp.route("/urls", methods=["GET", "POST"])
def list_or_create_urls():
    if request.method == "POST":
        data = request.get_json(silent=True)
        return _create_url(data)

    # GET — list urls
    query = Url.select()

    user_id = request.args.get("user_id")
    if user_id is not None:
        query = query.where(Url.user == int(user_id))

    is_active = request.args.get("is_active")
    if is_active is not None:
        query = query.where(Url.is_active == (is_active.lower() == "true"))

    # Pagination
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    query = query.order_by(Url.id).paginate(page, per_page)

    results = [_url_to_dict(u) for u in query]
    return jsonify(results)


@urls_bp.route("/urls/<int:url_id>", methods=["GET", "PUT", "DELETE"])
def get_update_delete_url(url_id):
    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify(error="URL not found", code="NOT_FOUND"), 404

    if request.method == "GET":
        result = _url_to_dict(url)
        result["event_count"] = Event.select().where(Event.url == url).count()
        return jsonify(result)

    if request.method == "PUT":
        data = request.get_json(silent=True)
        if not data:
            return jsonify(error="Request body must be JSON", code="VALIDATION_ERROR"), 400

        # Update allowed fields
        if "title" in data:
            url.title = data["title"]
        if "original_url" in data:
            if not is_valid_url(data["original_url"]):
                return jsonify(error="Invalid URL format", code="VALIDATION_ERROR"), 400
            url.original_url = data["original_url"]
        if "is_active" in data:
            url.is_active = bool(data["is_active"])
            # Invalidate cache when deactivating
            if not url.is_active:
                cache_delete(f"url:{url.short_code}")

        url.updated_at = datetime.now(timezone.utc)
        url.save()
        return jsonify(_url_to_dict(url))

    if request.method == "DELETE":
        # Delete related events first
        Event.delete().where(Event.url == url).execute()
        cache_delete(f"url:{url.short_code}")
        url.delete_instance()
        return jsonify(message="URL deleted"), 200
