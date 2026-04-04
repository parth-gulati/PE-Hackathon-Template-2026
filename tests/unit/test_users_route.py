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
        assert data[0]["username"] == "alice"
        assert data[1]["username"] == "bob"

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


class TestGetUser:
    def test_returns_user_by_id(self, client):
        User.create(username="diana", email="diana@example.com", created_at="2025-01-01 00:00:00")
        response = client.get("/users/1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "diana"
        assert data["email"] == "diana@example.com"

    def test_returns_404_for_missing_user(self, client):
        response = client.get("/users/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert data["code"] == "NOT_FOUND"

    def test_404_returns_json(self, client):
        response = client.get("/users/99999")
        assert response.content_type == "application/json"
