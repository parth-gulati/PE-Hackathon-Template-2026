"""Unit tests for /events endpoints."""

import pytest
import flask
from peewee import SqliteDatabase

from app.database import db
from app.models import Event, Url, User
from app.routes.events import events_bp

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
    app.register_blueprint(events_bp)

    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    return app.test_client()


@pytest.fixture
def sample_user():
    return User.create(username="evtuser", email="evt@example.com", created_at="2025-01-01 00:00:00")


@pytest.fixture
def sample_url(sample_user):
    return Url.create(
        user=sample_user, short_code="EVTTST", original_url="https://example.com",
        title="Event Test", is_active=True, created_at="2025-01-01", updated_at="2025-01-01",
    )


@pytest.fixture
def inactive_url(sample_user):
    return Url.create(
        user=sample_user, short_code="INACTV", original_url="https://example.com/off",
        title="Inactive", is_active=False, created_at="2025-01-01", updated_at="2025-01-01",
    )


class TestListEvents:
    def test_returns_empty_list(self, client):
        response = client.get("/events")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_events(self, client, sample_user, sample_url):
        Event.create(url=sample_url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details='{}')
        response = client.get("/events")
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["event_type"] == "click"

    def test_filter_by_url_id(self, client, sample_user, sample_url):
        Event.create(url=sample_url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details='{}')
        response = client.get(f"/events?url_id={sample_url.id}")
        assert len(response.get_json()) == 1

    def test_filter_by_user_id(self, client, sample_user, sample_url):
        Event.create(url=sample_url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details='{}')
        response = client.get(f"/events?user_id={sample_user.id}")
        assert len(response.get_json()) == 1

    def test_filter_by_event_type(self, client, sample_user, sample_url):
        Event.create(url=sample_url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details='{}')
        Event.create(url=sample_url, user=sample_user, event_type="created",
                     timestamp="2025-01-01", details='{}')
        response = client.get("/events?event_type=click")
        assert len(response.get_json()) == 1

    def test_event_has_url_id_and_user_id(self, client, sample_user, sample_url):
        Event.create(url=sample_url, user=sample_user, event_type="click",
                     timestamp="2025-01-01", details='{}')
        data = client.get("/events").get_json()[0]
        assert "url_id" in data
        assert "user_id" in data


class TestCreateEvent:
    def test_creates_event(self, client, sample_user, sample_url):
        response = client.post("/events", json={
            "url_id": sample_url.id,
            "user_id": sample_user.id,
            "event_type": "click",
            "details": {"referrer": "google.com"},
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["event_type"] == "click"
        assert data["url_id"] == sample_url.id

    def test_rejects_missing_fields(self, client):
        response = client.post("/events", json={"event_type": "click"})
        assert response.status_code == 400

    def test_rejects_nonexistent_url(self, client, sample_user):
        response = client.post("/events", json={
            "url_id": 99999, "user_id": sample_user.id, "event_type": "click",
        })
        assert response.status_code == 400

    def test_rejects_nonexistent_user(self, client, sample_url):
        response = client.post("/events", json={
            "url_id": sample_url.id, "user_id": 99999, "event_type": "click",
        })
        assert response.status_code == 400

    def test_rejects_invalid_event_type(self, client, sample_user, sample_url):
        response = client.post("/events", json={
            "url_id": sample_url.id, "user_id": sample_user.id, "event_type": "invalid",
        })
        assert response.status_code == 400

    def test_rejects_click_on_inactive_url(self, client, sample_user, inactive_url):
        response = client.post("/events", json={
            "url_id": inactive_url.id, "user_id": sample_user.id, "event_type": "click",
        })
        assert response.status_code == 400

    def test_details_parsed_as_dict(self, client, sample_user, sample_url):
        response = client.post("/events", json={
            "url_id": sample_url.id, "user_id": sample_user.id, "event_type": "click",
            "details": {"key": "value"},
        })
        data = response.get_json()
        assert data["details"] == {"key": "value"}
