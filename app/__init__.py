import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.database import db, init_db
from app.routes import register_routes

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get("REDIS_URL", "memory://"),
)


def create_app():
    load_dotenv()

    app = Flask(__name__)

    default_limit = os.environ.get("RATE_LIMIT", "100/minute")
    app.config["RATELIMIT_DEFAULT"] = default_limit

    init_db(app)
    limiter.init_app(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=str(e.description) if hasattr(e, 'description') else "Bad request", code="VALIDATION_ERROR"), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Resource not found", code="NOT_FOUND"), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(error="Internal server error", code="INTERNAL_ERROR"), 500

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify(
            error="Too many requests",
            code="RATE_LIMITED",
        ), 429

    @app.route("/health")
    def health():
        try:
            db.execute_sql("SELECT 1")
            return jsonify(status="ok"), 200
        except Exception:
            return jsonify(status="error", message="Database unavailable"), 503

    return app
