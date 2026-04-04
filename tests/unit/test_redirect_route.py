"""Unit tests for /<short_code> redirect endpoint."""

import pytest
import flask
from peewee import SqliteDatabase

from app.database import db
from app.models import Event, Url, User
from app.routes.redirect import redirect_bp

test_db = SqliteDatabase(":memory:")


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
    app.register_blueprint(redirect_bp)

    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    return app.test_client()


@pytest.fixture
def sample_user():
    return User.create(username="redir_user", email="redir@example.com", created_at="2025-01-01 00:00:00")


@pytest.fixture
def active_url(sample_user):
    return Url.create(
        user=sample_user, short_code="AbCdEf", original_url="https://example.com/target",
        title="Active URL", is_active=True, created_at="2025-01-01", updated_at="2025-01-01",
    )


@pytest.fixture
def inactive_url(sample_user):
    return Url.create(
        user=sample_user, short_code="XyZ123", original_url="https://example.com/inactive",
        title="Inactive URL", is_active=False, created_at="2025-01-01", updated_at="2025-01-01",
    )


class TestRedirect:
    def test_redirects_active_url(self, client, active_url):
        response = client.get("/AbCdEf")
        assert response.status_code == 301
        assert response.headers["Location"] == "https://example.com/target"

    def test_logs_click_event(self, client, active_url):
        client.get("/AbCdEf")
        assert Event.select().count() == 1
        event = Event.select().first()
        assert event.event_type == "click"
        assert event.url_id == active_url.id

    def test_returns_410_for_inactive_url(self, client, inactive_url):
        response = client.get("/XyZ123")
        assert response.status_code == 410
        data = response.get_json()
        assert data["code"] == "INACTIVE"

    def test_no_event_logged_for_inactive(self, client, inactive_url):
        client.get("/XyZ123")
        assert Event.select().count() == 0

    def test_returns_404_for_nonexistent_code(self, client):
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert data["code"] == "NOT_FOUND"

    def test_no_event_logged_for_404(self, client):
        client.get("/nonexistent")
        assert Event.select().count() == 0

    def test_click_event_has_short_code_in_details(self, client, active_url):
        client.get("/AbCdEf")
        event = Event.select().first()
        assert "AbCdEf" in event.details
