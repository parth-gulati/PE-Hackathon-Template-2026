"""Unit tests for /shorten, /urls endpoints."""

import os

import pytest
import flask
from peewee import SqliteDatabase

from app.database import db
from app.models import Event, Url, User
from app.routes.urls import urls_bp

test_db = SqliteDatabase(":memory:")
TEST_API_KEY = "test-key-for-urls"


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


@pytest.fixture
def client():
    app = flask.Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(urls_bp)

    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    return app.test_client()


@pytest.fixture(autouse=True)
def set_api_key():
    os.environ["API_KEY"] = TEST_API_KEY
    yield
    os.environ.pop("API_KEY", None)


@pytest.fixture
def sample_user():
    return User.create(username="testuser", email="test@example.com", created_at="2025-01-01 00:00:00")


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}


# --- POST /shorten ---

class TestCreateShortUrl:
    def test_creates_url_successfully(self, client, sample_user, auth_headers):
        response = client.post("/shorten", json={
            "original_url": "https://example.com/long-page",
            "title": "Test Link",
            "user_id": sample_user.id,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert "short_code" in data
        assert data["original_url"] == "https://example.com/long-page"
        assert data["title"] == "Test Link"
        assert data["user_id"] == sample_user.id
        assert data["is_active"] is True

    def test_logs_creation_event(self, client, sample_user, auth_headers):
        client.post("/shorten", json={
            "original_url": "https://example.com/event-test",
            "title": "Event Test",
            "user_id": sample_user.id,
        }, headers=auth_headers)
        assert Event.select().count() == 1
        event = Event.select().first()
        assert event.event_type == "created"

    def test_rejects_missing_fields(self, client, sample_user, auth_headers):
        response = client.post("/shorten", json={"title": "No URL"}, headers=auth_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "original_url" in data["error"]

    def test_rejects_invalid_url(self, client, sample_user, auth_headers):
        response = client.post("/shorten", json={
            "original_url": "not-a-url",
            "title": "Bad URL",
            "user_id": sample_user.id,
        }, headers=auth_headers)
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_ERROR"

    def test_rejects_nonexistent_user(self, client, auth_headers):
        response = client.post("/shorten", json={
            "original_url": "https://example.com/page",
            "title": "No User",
            "user_id": 99999,
        }, headers=auth_headers)
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_ERROR"

    def test_rejects_non_json_body(self, client, auth_headers):
        response = client.post("/shorten", data="not json", content_type="text/plain",
                               headers=auth_headers)
        assert response.status_code == 400

    def test_generates_unique_short_codes(self, client, sample_user, auth_headers):
        codes = set()
        for _ in range(5):
            response = client.post("/shorten", json={
                "original_url": "https://example.com/unique",
                "title": "Unique Test",
                "user_id": sample_user.id,
            }, headers=auth_headers)
            codes.add(response.get_json()["short_code"])
        assert len(codes) == 5  # all unique


# --- GET /urls ---

class TestListUrls:
    def test_returns_empty_list(self, client):
        response = client.get("/urls")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_all_urls(self, client, sample_user):
        Url.create(user=sample_user, short_code="AAAAAA", original_url="https://a.com",
                    title="A", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        Url.create(user=sample_user, short_code="BBBBBB", original_url="https://b.com",
                    title="B", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        response = client.get("/urls")
        assert len(response.get_json()) == 2

    def test_filter_by_user_id(self, client):
        u1 = User.create(username="user1", email="u1@example.com", created_at="2025-01-01")
        u2 = User.create(username="user2", email="u2@example.com", created_at="2025-01-01")
        Url.create(user=u1, short_code="U1URL1", original_url="https://a.com",
                    title="A", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        Url.create(user=u2, short_code="U2URL1", original_url="https://b.com",
                    title="B", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        response = client.get(f"/urls?user_id={u1.id}")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["short_code"] == "U1URL1"

    def test_filter_by_is_active(self, client, sample_user):
        Url.create(user=sample_user, short_code="ACTIVE", original_url="https://a.com",
                    title="A", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        Url.create(user=sample_user, short_code="INACTV", original_url="https://b.com",
                    title="B", is_active=False, created_at="2025-01-01", updated_at="2025-01-01")
        response = client.get("/urls?is_active=true")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["short_code"] == "ACTIVE"

    def test_url_has_user_id_field(self, client, sample_user):
        Url.create(user=sample_user, short_code="UIDTST", original_url="https://a.com",
                    title="A", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        response = client.get("/urls")
        data = response.get_json()[0]
        assert "user_id" in data
        assert data["user_id"] == sample_user.id


# --- GET /urls/<id> ---

class TestGetUrl:
    def test_returns_url_by_id(self, client, sample_user):
        url = Url.create(user=sample_user, short_code="GETURL", original_url="https://a.com",
                         title="Get Test", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        response = client.get(f"/urls/{url.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["short_code"] == "GETURL"
        assert data["title"] == "Get Test"

    def test_includes_event_count(self, client, sample_user):
        url = Url.create(user=sample_user, short_code="EVTCNT", original_url="https://a.com",
                         title="Events", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        Event.create(url=url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details="{}")
        Event.create(url=url, user=sample_user, event_type="click",
                     timestamp="2025-01-02", details="{}")
        response = client.get(f"/urls/{url.id}")
        assert response.get_json()["event_count"] == 2

    def test_returns_404_for_missing_url(self, client):
        response = client.get("/urls/99999")
        assert response.status_code == 404
        assert response.get_json()["code"] == "NOT_FOUND"
