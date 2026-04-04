"""API key authentication middleware."""

import os
from functools import wraps

from flask import jsonify, request


def require_api_key(f):
    """Decorator that requires a valid X-API-Key header."""

    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = os.environ.get("API_KEY")
        provided_key = request.headers.get("X-API-Key")

        if not provided_key:
            return jsonify(error="API key required", code="AUTH_REQUIRED"), 401

        if provided_key != api_key:
            return jsonify(error="Invalid API key", code="AUTH_INVALID"), 403

        return f(*args, **kwargs)

    return decorated
