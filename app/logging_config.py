"""Structured JSON logging configuration."""

import logging
import json
import sys
import uuid
from datetime import datetime, timezone

from flask import g, request


class JSONFormatter(logging.Formatter):
    """Format log records as JSON with structured fields."""

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add request context if available
        try:
            log_entry["request_id"] = g.get("request_id", "no-request")
        except RuntimeError:
            log_entry["request_id"] = "no-request"

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(app):
    """Configure structured JSON logging for the Flask app."""
    # Remove default handlers
    app.logger.handlers.clear()
    logging.root.handlers.clear()

    # JSON handler to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.setLevel(logging.INFO)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Also configure root logger for libraries
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.WARNING)

    @app.before_request
    def _set_request_id():
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

    @app.after_request
    def _log_request(response):
        app.logger.info(
            "%s %s %s",
            request.method,
            request.path,
            response.status_code,
        )
        return response
