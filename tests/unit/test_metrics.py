"""Unit tests for Prometheus metrics."""

import flask
from app.metrics import metrics_bp, setup_metrics, REQUEST_COUNT, ACTIVE_REQUESTS


class TestMetricsEndpoint:
    def setup_method(self):
        app = flask.Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(metrics_bp)
        setup_metrics(app)
        self.client = app.test_client()

    def test_metrics_returns_200(self):
        response = self.client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_returns_prometheus_format(self):
        response = self.client.get("/metrics")
        assert "text/plain" in response.content_type

    def test_metrics_contains_request_count(self):
        response = self.client.get("/metrics")
        body = response.data.decode()
        assert "http_requests_total" in body

    def test_metrics_contains_latency(self):
        response = self.client.get("/metrics")
        body = response.data.decode()
        assert "http_request_duration_seconds" in body

    def test_metrics_contains_active_requests(self):
        response = self.client.get("/metrics")
        body = response.data.decode()
        assert "http_active_requests" in body

    def test_metrics_contains_error_count(self):
        response = self.client.get("/metrics")
        body = response.data.decode()
        assert "http_errors_total" in body
