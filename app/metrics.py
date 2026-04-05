"""Prometheus metrics for the Flask app."""

import time

from flask import Blueprint, g, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

metrics_bp = Blueprint("metrics", __name__)

# Counters
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

ERROR_COUNT = Counter(
    "http_errors_total",
    "Total HTTP errors (4xx and 5xx)",
    ["method", "endpoint", "status"],
)

# Histogram for response times
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Gauge for active connections
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of active HTTP requests",
)


def setup_metrics(app):
    """Register metrics hooks with the Flask app."""

    @app.before_request
    def _start_timer():
        g.start_time = time.time()
        ACTIVE_REQUESTS.inc()

    @app.after_request
    def _record_metrics(response):
        latency = time.time() - g.get("start_time", time.time())
        endpoint = request.endpoint or "unknown"

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(latency)

        if response.status_code >= 400:
            ERROR_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()

        ACTIVE_REQUESTS.dec()
        return response


@metrics_bp.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": "text/plain; version=0.0.4"}
