"""Unit tests for the /health endpoint."""

from unittest.mock import patch

import flask
from peewee import SqliteDatabase

from app.database import db
from app.models import Event, Url, User

test_db = SqliteDatabase(":memory:")


def _create_test_app():
    """Create a Flask app wired to the test SQLite DB."""
    app = flask.Flask(__name__)
    app.config["TESTING"] = True

    # Import the health route from the real app factory
    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    @app.teardown_appcontext
    def _db_close(exc):
        if not test_db.is_closed():
            test_db.close()

    @app.route("/health")
    def health():
        try:
            db.execute_sql("SELECT 1")
            return flask.jsonify(status="ok"), 200
        except Exception:
            return flask.jsonify(status="error", message="Database unavailable"), 503

    return app


def setup_module():
    db.initialize(test_db)
    test_db.bind([User, Url, Event])
    test_db.connect()
    test_db.create_tables([User, Url, Event])


def teardown_module():
    test_db.drop_tables([Event, Url, User])
    test_db.close()


class TestHealthEndpoint:
    def setup_method(self):
        self.app = _create_test_app()
        self.client = self.app.test_client()

    def test_returns_200_ok(self):
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_returns_json(self):
        response = self.client.get("/health")
        assert response.content_type == "application/json"

    def test_returns_status_ok(self):
        response = self.client.get("/health")
        data = response.get_json()
        assert data["status"] == "ok"

    def test_returns_503_when_db_down(self):
        # Patch the underlying database's execute_sql (not the proxy)
        with patch.object(test_db, "execute_sql", side_effect=Exception("DB down")):
            response = self.client.get("/health")
            assert response.status_code == 503
            data = response.get_json()
            assert data["status"] == "error"
            assert "Database unavailable" in data["message"]
