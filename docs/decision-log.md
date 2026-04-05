# Decision Log

## Flask

**Why:** Provided by the hackathon template. Lightweight, minimal boilerplate, well-suited for an API backend. No need for Django's ORM or admin panel — Peewee handles the data layer.

## Peewee ORM

**Why:** Provided by the hackathon template. Lightweight alternative to SQLAlchemy. Direct model-to-table mapping, simple query syntax, built-in connection management. `model_to_dict` from playhouse makes JSON serialization trivial.

## PostgreSQL

**Why:** Provided by the hackathon template. Production-grade relational database. Handles concurrent connections well, supports proper constraints (unique, foreign keys), and indexes. Essential for the scalability quest.

## Redis

**Why:** Two purposes: (1) Cache frequently accessed redirect lookups to avoid hitting PostgreSQL on every short code resolution. (2) Shared rate limiter backend so all app instances enforce the same limits. Chose Redis over Memcached for its richer data structures and built-in TTL support.

**Alternative considered:** No caching — rejected because redirect is the hot path and would bottleneck at 500 users.

## Nginx

**Why:** Industry-standard reverse proxy and load balancer. Round-robin distribution across app instances. Handles static content, connection pooling, and upstream health checks. Simple config, proven at scale.

**Alternative considered:** Traefik — more features (auto-discovery, Let's Encrypt) but overkill for a hackathon. HAProxy — similar capability but less ecosystem support for our use case.

## Gunicorn

**Why:** Flask's dev server is single-threaded. Gunicorn provides pre-fork worker model with multiple workers and threads. 8 workers × 4 threads × 2 containers = 64 concurrent request handlers. Production-standard WSGI server for Python.

**Alternative considered:** uWSGI — similar capability but more complex configuration.

## Locust

**Why:** Python-native load testing tool. Fits our stack (no context switching to JavaScript for k6). Web UI for real-time monitoring. Easy to script complex user scenarios. The hackathon quest accepts either Locust or k6.

**Alternative considered:** k6 — better performance at extreme scale, but requires JavaScript and we're a Python project.

## Prometheus + Grafana

**Why:** Industry-standard monitoring stack. Prometheus scrapes our `/metrics` endpoint every 15 seconds. Grafana visualizes the four golden signals (Traffic, Latency, Errors, Saturation). Both run as Docker containers with zero code changes to the app — just expose `/metrics`.

**Alternative considered:** Datadog — SaaS monitoring, easier setup but requires account and API key. Overkill for a hackathon.

## pytest

**Why:** Python testing standard. Simple assertions, powerful fixtures, excellent plugin ecosystem (pytest-cov for coverage). Test discovery is automatic. Runs in CI with zero configuration beyond `testpaths = ["tests"]`.

## GitHub Actions

**Why:** Built into GitHub where the repo lives. Free for public repos. YAML-based configuration. PostgreSQL service container for integration tests. Coverage gating with `--cov-fail-under=70`.

## API Key Authentication (not JWT)

**Why:** Simplest auth mechanism that proves the concept. API key in header, checked against environment variable. No token issuance, no expiry, no refresh flow. The evaluator tests that bad/missing keys are rejected — JWT would add complexity without additional points.

## Pagination on List Endpoints

**Why:** Without pagination, `GET /urls` returns all 2000 records per request. Under 50 concurrent users, that's 50 simultaneous full-table dumps — causing timeouts and 502s. Default page size of 20 items reduced response payload by 99%.
