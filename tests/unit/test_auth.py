"""Unit tests for API key authentication."""

import os

import pytest
import flask
from peewee import SqliteDatabase

from app.auth import require_api_key
from app.database import db
from app.models import Event, Url, User
from app.routes.urls import urls_bp

test_db = SqliteDatabase(":memory:")
TEST_API_KEY = "test-secret-key"


def setup_module():
    db.initialize(test_db)
    test_db.bind([User, Url, Event])
    test_db.connect()
    test_db.create_tables([User, Url, Event])


def teardown_module():
    test_db.drop_tables([Event, Url, User])
    test_db.close()


@pytest.fixture(autouse=True)
def clean_tables():
    test_db.drop_tables([Event, Url, User])
    test_db.create_tables([User, Url, Event])
    yield


@pytest.fixture(autouse=True)
def set_api_key():
    os.environ["API_KEY"] = TEST_API_KEY
    yield
    os.environ.pop("API_KEY", None)


@pytest.fixture
def client():
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(urls_bp)

    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    return app.test_client()


@pytest.fixture
def sample_user():
    return User.create(username="authuser", email="auth@example.com", created_at="2025-01-01 00:00:00")


class TestApiKeyAuth:
    def test_rejects_missing_api_key(self, client, sample_user):
        response = client.post("/shorten", json={
            "original_url": "https://example.com",
            "title": "No Key",
            "user_id": sample_user.id,
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "AUTH_REQUIRED"
        assert "API key required" in data["error"]

    def test_rejects_invalid_api_key(self, client, sample_user):
        response = client.post("/shorten", json={
            "original_url": "https://example.com",
            "title": "Wrong Key",
            "user_id": sample_user.id,
        }, headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403
        data = response.get_json()
        assert data["code"] == "AUTH_INVALID"

    def test_accepts_valid_api_key(self, client, sample_user):
        response = client.post("/shorten", json={
            "original_url": "https://example.com",
            "title": "Valid Key",
            "user_id": sample_user.id,
        }, headers={"X-API-Key": TEST_API_KEY})
        assert response.status_code == 201

    def test_read_endpoints_no_auth_required(self, client, sample_user):
        Url.create(user=sample_user, short_code="NOAUTH", original_url="https://a.com",
                    title="Open", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        # /urls — no API key needed
        response = client.get("/urls")
        assert response.status_code == 200

        # /urls/<id> — no API key needed
        response = client.get("/urls/1")
        assert response.status_code == 200
