# Failure Modes Documentation

## 1. Database Unavailable

**Symptom:** `/health` returns `503` with `{"status": "error", "message": "Database unavailable"}`. All endpoints that query the DB return 500.

**Cause:** PostgreSQL container is down, network partition, or connection pool exhausted.

**Response:** The health endpoint detects this via `SELECT 1` probe and returns 503 instead of crashing. Other endpoints return `{"error": "Internal server error", "code": "INTERNAL_ERROR"}` — no stack traces leaked.

**Recovery:** Docker restart policy (`restart: always`) brings the app back once Postgres is reachable. `depends_on: condition: service_healthy` prevents the app from starting before Postgres is ready.

## 2. App Container Killed

**Symptom:** No response from the service. Health checks fail.

**Cause:** OOM kill, manual `docker kill`, or host resource exhaustion.

**Response:** Docker's `restart: always` policy automatically restarts the container.

**Recovery:** Service returns to healthy state within ~30 seconds. No data loss — all state is in PostgreSQL, not in the app process. Verify with `curl http://localhost:5000/health`.

## 3. Bad Input Flood

**Symptom:** High volume of 400-level responses in logs. Possible increased latency.

**Cause:** Client sending malformed JSON, missing fields, invalid URLs, or nonexistent user IDs.

**Response:** Every invalid request gets a structured JSON error with the appropriate HTTP status code (400, 401, 403, 409, 410). The app never crashes on bad input — all request parsing is wrapped in validation before touching the database.

**Recovery:** No recovery needed — the service handles this automatically. Rate limiting (`flask-limiter`) caps request volume per IP. If abuse persists, the client receives `429 Too Many Requests`.

## 4. Rate Limit Exceeded

**Symptom:** Client receives `429` with `{"error": "Too many requests", "code": "RATE_LIMITED"}`.

**Cause:** Client exceeded the configured rate limit (default: 100 req/min for reads, 30 req/min for POST /shorten).

**Response:** Clean JSON error with `Retry-After` header indicating when to retry.

**Recovery:** Automatic — client waits and retries. Rate limits reset per the configured window. Limits are configurable via `RATE_LIMIT` environment variable.

## 5. Short Code Collision

**Symptom:** Internal retry during `POST /shorten` (not visible to client).

**Cause:** Randomly generated short code already exists in the database (extremely rare with 62^6 = 56B possible codes).

**Response:** The system automatically retries with a new random code, up to 10 attempts. The unique constraint on `short_code` at the database level prevents duplicates even under concurrent requests.

**Recovery:** Transparent to the client. If all 10 retries fail (near-impossible), returns `500` with `{"error": "Failed to generate unique short code"}`.

## 6. Invalid API Key

**Symptom:** Client receives `401` or `403` on write endpoints.

**Cause:** Missing or incorrect `X-API-Key` header on `POST /shorten`.

**Response:**
- Missing key: `401 {"error": "API key required", "code": "AUTH_REQUIRED"}`
- Wrong key: `403 {"error": "Invalid API key", "code": "AUTH_INVALID"}`

**Recovery:** Client provides the correct API key. Read endpoints (`GET /urls`, `GET /users`, redirects) don't require auth.
