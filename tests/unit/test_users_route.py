"""Unit tests for /users endpoints."""

import pytest
import flask
from peewee import SqliteDatabase

from app.database import db
from app.models import Event, Url, User
from app.routes.users import users_bp

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
    app.register_blueprint(users_bp)

    @app.before_request
    def _db_connect():
        test_db.connect(reuse_if_open=True)

    return app.test_client()


@pytest.fixture
def sample_user():
    return User.create(username="testuser", email="test@example.com", created_at="2025-01-01 00:00:00")


class TestListUsers:
    def test_returns_empty_list(self, client):
        response = client.get("/users")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_returns_all_users(self, client):
        User.create(username="alice", email="alice@example.com", created_at="2025-01-01 00:00:00")
        User.create(username="bob", email="bob@example.com", created_at="2025-01-02 00:00:00")
        response = client.get("/users")
        data = response.get_json()
        assert len(data) == 2

    def test_returns_json(self, client):
        response = client.get("/users")
        assert response.content_type == "application/json"

    def test_user_fields_present(self, client):
        User.create(username="charlie", email="charlie@example.com", created_at="2025-01-01 00:00:00")
        response = client.get("/users")
        user = response.get_json()[0]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "created_at" in user

    def test_pagination(self, client):
        for i in range(25):
            User.create(username=f"user{i}", email=f"u{i}@example.com", created_at="2025-01-01")
        response = client.get("/users?page=1&per_page=10")
        assert len(response.get_json()) == 10


class TestGetUser:
    def test_returns_user_by_id(self, client, sample_user):
        response = client.get(f"/users/{sample_user.id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_returns_404_for_missing_user(self, client):
        response = client.get("/users/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["code"] == "NOT_FOUND"

    def test_404_returns_json(self, client):
        response = client.get("/users/99999")
        assert response.content_type == "application/json"


class TestCreateUser:
    def test_creates_user(self, client):
        response = client.post("/users", json={
            "username": "newuser",
            "email": "new@example.com",
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_rejects_missing_fields(self, client):
        response = client.post("/users", json={"username": "nomail"})
        assert response.status_code == 400
        assert response.get_json()["code"] == "VALIDATION_ERROR"


class TestUpdateUser:
    def test_update_username(self, client, sample_user):
        response = client.put(f"/users/{sample_user.id}", json={"username": "updated"})
        assert response.status_code == 200
        assert response.get_json()["username"] == "updated"

    def test_update_email(self, client, sample_user):
        response = client.put(f"/users/{sample_user.id}", json={"email": "new@example.com"})
        assert response.status_code == 200
        assert response.get_json()["email"] == "new@example.com"

    def test_update_404(self, client):
        response = client.put("/users/99999", json={"username": "nope"})
        assert response.status_code == 404


class TestDeleteUser:
    def test_delete_user(self, client, sample_user):
        response = client.delete(f"/users/{sample_user.id}")
        assert response.status_code == 200
        assert User.select().count() == 0

    def test_delete_cascades_urls_and_events(self, client, sample_user):
        url = Url.create(user=sample_user, short_code="DELUSR", original_url="https://a.com",
                         title="Del", is_active=True, created_at="2025-01-01", updated_at="2025-01-01")
        Event.create(url=url, user=sample_user, event_type="click", timestamp="2025-01-01", details="{}")
        client.delete(f"/users/{sample_user.id}")
        assert User.select().count() == 0
        assert Url.select().count() == 0
        assert Event.select().count() == 0

    def test_delete_404(self, client):
        response = client.delete("/users/99999")
        assert response.status_code == 404


class TestBulkUpload:
    def test_bulk_json(self, client):
        response = client.post("/users/bulk", json=[
            {"username": "bulk1", "email": "b1@example.com"},
            {"username": "bulk2", "email": "b2@example.com"},
        ])
        assert response.status_code == 201
        assert User.select().count() == 2
