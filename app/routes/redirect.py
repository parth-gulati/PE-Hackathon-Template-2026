from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect

from app.cache import cache_delete, cache_get, cache_set
from app.models.event import Event
from app.models.url import Url

redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route("/<short_code>")
def redirect_short_url(short_code):
    # Try cache first
    cached = cache_get(f"url:{short_code}")
    if cached:
        if not cached["is_active"]:
            return jsonify(error="This short URL is no longer active", code="INACTIVE"), 410

        Event.create(
            url=cached["id"],
            user=cached["user_id"],
            event_type="click",
            timestamp=datetime.now(timezone.utc),
            details=f'{{"short_code":"{short_code}"}}',
        )
        return redirect(cached["original_url"], code=301)

    # Cache miss — hit DB
    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        return jsonify(error="Short URL not found", code="NOT_FOUND"), 404

    # Cache the result
    cache_set(f"url:{short_code}", {
        "id": url.id,
        "user_id": url.user_id,
        "original_url": url.original_url,
        "is_active": url.is_active,
    })

    if not url.is_active:
        return jsonify(error="This short URL is no longer active", code="INACTIVE"), 410

    Event.create(
        url=url,
        user=url.user_id,
        event_type="click",
        timestamp=datetime.now(timezone.utc),
        details=f'{{"short_code":"{short_code}"}}',
    )

    return redirect(url.original_url, code=301)
