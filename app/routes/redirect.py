from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect

from app.models.event import Event
from app.models.url import Url

redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route("/<short_code>")
def redirect_short_url(short_code):
    try:
        url = Url.get(Url.short_code == short_code)
    except Url.DoesNotExist:
        return jsonify(error="Short URL not found", code="NOT_FOUND"), 404

    if not url.is_active:
        return jsonify(error="This short URL is no longer active", code="INACTIVE"), 410

    # Log click event
    Event.create(
        url=url,
        user=url.user_id,
        event_type="click",
        timestamp=datetime.now(timezone.utc),
        details=f'{{"short_code":"{short_code}"}}',
    )

    return redirect(url.original_url, code=301)
