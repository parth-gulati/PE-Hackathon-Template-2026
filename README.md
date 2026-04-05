# URL Shortener — Production Engineering Hackathon

A production-grade URL shortener API demonstrating operational excellence: comprehensive testing, horizontal scaling, structured observability, and chaos resilience.

## Architecture

```
                    ┌──────────┐
                    │  Locust  │ (load testing)
                    └────┬─────┘
                         │
                    ┌────▼─────┐
   ┌───────────────►│  Nginx   │ (load balancer, port 80)
   │                └────┬─────┘
   │           ┌─────────┴─────────┐
   │      ┌────▼─────┐       ┌────▼─────┐
   │      │  App 1   │       │  App 2   │ (gunicorn, 8 workers × 4 threads)
   │      └────┬─────┘       └────┬─────┘
   │           │                  │
   │      ┌────▼──────────────────▼────┐
   │      │        PostgreSQL          │ (port 5432)
   │      └────────────────────────────┘
   │      ┌────────────────────────────┐
   │      │          Redis             │ (port 6379, caching + rate limiting)
   │      └────────────────────────────┘
   │
   │      ┌────────────────────────────┐
   ├──────│       Prometheus           │ (port 9090, scrapes /metrics)
   │      └────────────┬───────────────┘
   │      ┌────────────▼───────────────┐
   └──────│        Grafana             │ (port 3001, dashboards)
          └────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/parth-gulati/PE-Hackathon-Template-2026.git
cd PE-Hackathon-Template-2026

# 2. Start all services
docker-compose up --build -d

# 3. Wait for healthy postgres, then restart nginx (podman DNS fix)
sleep 5
docker-compose restart nginx

# 4. Seed the database
docker-compose exec app1 uv run python seed_data.py

# 5. Verify
curl http://localhost/health
# → {"status": "ok"}
```

## Local Development (without Docker)

```bash
# 1. Install dependencies
uv sync

# 2. Create database
createdb hackathon_db

# 3. Configure environment
cp .env.example .env

# 4. Run the server
uv run run.py

# 5. Run tests
uv run pytest -v
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/health` | None | Health check with DB connectivity verification |
| `POST` | `/shorten` | API Key | Create a short URL |
| `GET` | `/<short_code>` | None | Redirect to original URL (301) |
| `GET` | `/urls` | None | List URLs (paginated, filterable by `user_id`, `is_active`) |
| `GET` | `/urls/<id>` | None | URL details with event count |
| `GET` | `/users` | None | List users (paginated) |
| `GET` | `/users/<id>` | None | User details |
| `GET` | `/metrics` | None | Prometheus metrics |

### Authentication

Write endpoints require `X-API-Key` header. Set the key via `API_KEY` environment variable (default: `dev-api-key-change-me`).

```bash
curl -X POST http://localhost/shorten \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-me" \
  -d '{"original_url": "https://example.com", "title": "My Link", "user_id": 1}'
```

### Error Responses

All errors return structured JSON:

```json
{"error": "Human-readable message", "code": "ERROR_CODE"}
```

| Status | Code | Meaning |
|--------|------|---------|
| 400 | `VALIDATION_ERROR` | Bad input |
| 401 | `AUTH_REQUIRED` | Missing API key |
| 403 | `AUTH_INVALID` | Wrong API key |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 410 | `INACTIVE` | URL is deactivated |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error (no stack trace exposed) |

## Monitoring

- **Grafana Dashboard:** http://localhost:3001 (no login required, auto-provisioned)
- **Prometheus:** http://localhost:9090
- **Locust:** `uv run locust --host=http://localhost` → http://localhost:8089

The Grafana dashboard shows the four golden signals: Traffic, Latency, Errors, Saturation.

## Testing

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_urls_route.py -v
```

**105 tests | 78% coverage | CI blocks deploys below 70%**

## Load Testing

```bash
uv run locust --host=http://localhost
# Open http://localhost:8089
# Set users: 50 (Bronze), 200 (Silver), 500 (Gold)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | Database host |
| `DATABASE_PORT` | `5432` | Database port |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `postgres` | Database password |
| `API_KEY` | `dev-api-key-change-me` | API key for write endpoints |
| `RATE_LIMIT` | `1000/minute` | Default rate limit |
| `REDIS_URL` | `memory://` | Redis URL for caching and rate limiting |
| `CACHE_TTL` | `300` | Redis cache TTL in seconds |

## Project Structure

```
├── app/
│   ├── __init__.py          # App factory, error handlers, rate limiting
│   ├── auth.py              # API key authentication decorator
│   ├── cache.py             # Redis caching with graceful degradation
│   ├── database.py          # Peewee database proxy and connection hooks
│   ├── logging_config.py    # Structured JSON logging
│   ├── metrics.py           # Prometheus metrics and /metrics endpoint
│   ├── utils.py             # Short code generation, URL validation
│   ├── models/
│   │   ├── user.py          # User model
│   │   ├── url.py           # URL model (unique short_code, indexed)
│   │   └── event.py         # Event model (click/create tracking)
│   └── routes/
│       ├── users.py         # GET /users, /users/<id>
│       ├── urls.py          # POST /shorten, GET /urls, /urls/<id>
│       └── redirect.py      # GET /<short_code> with caching
├── tests/
│   └── unit/                # 105 unit tests
├── docs/
│   ├── failure-modes.md     # What breaks and how it recovers
│   └── runbook.md           # Emergency response guide
├── nginx/nginx.conf         # Load balancer config
├── prometheus/prometheus.yml # Metrics scraping config
├── grafana/                 # Dashboard auto-provisioning
├── docker-compose.yml       # Full stack: postgres, redis, app×2, nginx, prometheus, grafana
├── Dockerfile               # Python 3.13 + uv + gunicorn
├── locustfile.py            # Load test scenarios
└── seed_data.py             # CSV import with sequence fix
```

## Tech Stack

**Application:** Flask, Peewee ORM, PostgreSQL, Redis, gunicorn
**Infrastructure:** Docker Compose, Nginx, Prometheus, Grafana
**Testing:** pytest (105 tests, 78% coverage), Locust (load testing)
**CI/CD:** GitHub Actions (auto-test on push, 70% coverage gate)
