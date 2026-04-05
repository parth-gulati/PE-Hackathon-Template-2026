"""Unit tests for structured JSON logging."""

import json

import flask
from app.logging_config import JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_formats_as_json(self):
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "test message", (), None)
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"

    def test_includes_timestamp(self):
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        parsed = json.loads(formatter.format(record))
        assert "timestamp" in parsed

    def test_includes_request_id(self):
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        parsed = json.loads(formatter.format(record))
        assert "request_id" in parsed

    def test_error_level(self):
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.ERROR, "", 0, "error msg", (), None)
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "ERROR"

    def test_warning_level(self):
        import logging
        formatter = JSONFormatter()
        record = logging.LogRecord("test", logging.WARNING, "", 0, "warn msg", (), None)
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "WARNING"


class TestSetupLogging:
    def test_adds_request_id(self):
        app = flask.Flask(__name__)
        app.config["TESTING"] = True
        setup_logging(app)

        with app.test_client() as client:
            @app.route("/test-log")
            def test_route():
                from flask import g
                return flask.jsonify(request_id=g.get("request_id", "none"))

            response = client.get("/test-log")
            data = response.get_json()
            assert data["request_id"] != "none"

    def test_logs_requests(self):
        app = flask.Flask(__name__)
        app.config["TESTING"] = True
        setup_logging(app)

        @app.route("/test-log2")
        def test_route2():
            return "ok"

        with app.test_client() as client:
            client.get("/test-log2")
            # If we get here without error, logging didn't crash
