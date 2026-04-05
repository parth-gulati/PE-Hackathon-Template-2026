"""Unit tests for API key authentication decorator."""

import os

import pytest
import flask

from app.auth import require_api_key

TEST_API_KEY = "test-secret-key"


@pytest.fixture
def app():
    app = flask.Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected", methods=["POST"])
    @require_api_key
    def protected():
        return flask.jsonify(message="ok"), 200

    @app.route("/open")
    def open_route():
        return flask.jsonify(message="ok"), 200

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def set_api_key():
    os.environ["API_KEY"] = TEST_API_KEY
    yield
    os.environ.pop("API_KEY", None)


class TestApiKeyAuth:
    def test_rejects_missing_api_key(self, client):
        response = client.post("/protected")
        assert response.status_code == 401
        data = response.get_json()
        assert data["code"] == "AUTH_REQUIRED"

    def test_rejects_invalid_api_key(self, client):
        response = client.post("/protected", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403
        data = response.get_json()
        assert data["code"] == "AUTH_INVALID"

    def test_accepts_valid_api_key(self, client):
        response = client.post("/protected", headers={"X-API-Key": TEST_API_KEY})
        assert response.status_code == 200

    def test_open_endpoint_no_auth(self, client):
        response = client.get("/open")
        assert response.status_code == 200
