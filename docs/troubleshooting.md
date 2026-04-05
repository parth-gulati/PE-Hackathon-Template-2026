# Troubleshooting

## "502 Bad Gateway" from Nginx

**Cause:** Nginx resolved app container IPs at startup, but Podman assigned new IPs.

**Fix:**
```bash
docker-compose restart nginx
```

## "no live upstreams" in Nginx logs

**Cause:** Same as above — stale DNS resolution.

**Fix:**
```bash
docker-compose restart nginx
```

## POST /shorten returns "Failed to generate unique short code"

**Cause:** PostgreSQL auto-increment sequence is behind the seeded data IDs.

**Fix:** Re-run the seed script which resets sequences:
```bash
docker-compose down -v
docker-compose up --build -d
sleep 5
docker-compose exec app1 uv run python seed_data.py
```

## All endpoints return 500

**Cause:** Database tables don't exist or database is unreachable.

**Fix:**
1. Check postgres: `docker-compose logs postgres --tail 10`
2. Check if tables exist: `docker-compose exec app1 uv run python setup_db.py`
3. Seed data: `docker-compose exec app1 uv run python seed_data.py`

## Rate limiting (429 Too Many Requests)

**Cause:** Client exceeded the configured rate limit.

**Not a bug.** This is correct behavior. Adjust limits via environment variable:
```bash
RATE_LIMIT="5000/minute" docker-compose up -d
```

## Locust shows high failure rate

**Check:**
1. Are the failures 429s? That's rate limiting, not errors.
2. Are the failures 410s on `/<short_code>`? That's inactive URLs, correct behavior.
3. Are the failures 502s? Restart nginx.
4. Are the failures 500s? Check app logs: `docker-compose logs app1 --tail 50`

## Grafana shows "No data"

**Check:**
1. Is Prometheus running? http://localhost:9090
2. Are targets UP? http://localhost:9090/targets
3. Is traffic flowing? Run Locust to generate data.
4. Restart: `docker-compose restart grafana`

## Tests fail locally but pass in CI

**Cause:** Local PostgreSQL connection vs CI PostgreSQL service container.

Unit tests use in-memory SQLite, so they should pass without PostgreSQL. If they fail:
```bash
uv sync
uv run pytest tests/unit/ -v
```

## Port already in use

**Fix:** Find and kill the process:
```bash
lsof -i :5000  # or :80, :3001, :9090
kill <PID>
```

Or change the port in `docker-compose.yml`.

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_NAME` | `hackathon_db` | PostgreSQL database name |
| `DATABASE_HOST` | `localhost` | Database host (`postgres` in Docker) |
| `DATABASE_PORT` | `5432` | Database port |
| `DATABASE_USER` | `postgres` | Database user |
| `DATABASE_PASSWORD` | `postgres` | Database password |
| `API_KEY` | `dev-api-key-change-me` | API key for write endpoints |
| `RATE_LIMIT` | `1000/minute` | Default rate limit per IP |
| `REDIS_URL` | `memory://` | Redis connection URL |
| `CACHE_TTL` | `300` | Redis cache TTL (seconds) |
