# Runbook — Emergency Response Guide

## Alert: Service Down

**What it means:** The `/health` endpoint is not returning 200 OK. The app is unreachable or the database connection is broken.

**Diagnosis:**
1. Check if containers are running: `docker-compose ps`
2. Check app logs: `docker-compose logs app1 --tail 50`
3. Check if postgres is healthy: `docker-compose exec postgres pg_isready`
4. Check if the app can reach postgres: `docker-compose exec app1 curl -s http://localhost:5000/health`

**Fix:**
- If containers are stopped: `docker-compose up -d`
- If postgres is down: `docker-compose restart postgres` then `docker-compose restart app1 app2`
- If app is crash-looping: check logs for Python errors, fix code, rebuild: `docker-compose up --build -d`
- If DNS issue (podman): `docker-compose restart nginx`

**Escalation:** If none of the above works, check host resources (`docker stats`). If the host is out of memory/CPU, scale down workers in Dockerfile.

---

## Alert: High Error Rate (>10% for 2+ minutes)

**What it means:** More than 10% of requests are returning 4xx/5xx errors.

**Diagnosis:**
1. Check which endpoints are failing: look at `/metrics` for `http_errors_total` by endpoint
2. Check app logs for ERROR level entries: `docker-compose logs app1 --tail 100 | grep ERROR`
3. Check if it's rate limiting (429s are expected under heavy load)
4. Check database connections: `docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity"`

**Fix:**
- If 429s dominate: this is rate limiting working correctly. Increase `RATE_LIMIT` env var if needed.
- If 500s dominate: check logs for the actual exception. Common causes:
  - Database connection pool exhausted → restart app containers
  - Sequence collision after re-seeding → run sequence reset in seed_data.py
- If 502s dominate: nginx can't reach app containers → `docker-compose restart nginx`

**Escalation:** If errors persist, check `docker stats` for resource exhaustion.

---

## Alert: High Latency (p95 > 3 seconds)

**What it means:** 95th percentile response time exceeds 3 seconds. Users experience slow service.

**Diagnosis:**
1. Check `/metrics` for `http_request_duration_seconds` histogram
2. Identify slow endpoints: which endpoint has the highest latency?
3. Check Redis: `docker-compose exec redis redis-cli ping` — if Redis is down, redirects hit DB every time
4. Check postgres: `docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity"` — connection pool full?

**Fix:**
- If `/urls` is slow: verify pagination is working (should return 20 items, not 2000)
- If `/<short_code>` is slow: check Redis is running and caching is active
- If all endpoints are slow: host is overloaded. Check `docker stats`. Scale down Locust users or add more app instances.

**Escalation:** If latency persists after Redis/pagination fixes, the bottleneck is likely PostgreSQL. Consider adding read replicas (post-hackathon).

---

## Alert: High Saturation (CPU/Memory > 90%)

**What it means:** Host resources are near exhaustion. Service degradation is imminent.

**Diagnosis:**
1. Run `docker stats` to see per-container CPU and memory usage
2. Identify the hottest container

**Fix:**
- If postgres is hot: too many concurrent queries. Reduce gunicorn workers or add Redis caching for more endpoints.
- If app containers are hot: reduce workers in Dockerfile (`-w 4` instead of `-w 8`) or add a third app instance.
- If nginx is hot: unlikely, but check if it's buffering large responses.

**Escalation:** Add more app replicas in docker-compose.yml or reduce concurrent test load.

---

## General: How to Check Service Status

```bash
# All containers running?
docker-compose ps

# Health check
curl http://localhost/health

# Metrics
curl http://localhost/metrics

# Logs (last 50 lines)
docker-compose logs --tail 50

# Resource usage
docker stats --no-stream
```
