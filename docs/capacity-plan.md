# Capacity Plan

## Current Tested Limits

| Metric | Value | Configuration |
|--------|-------|---------------|
| Max tested concurrent users | 500 | Locust load test |
| App instances | 2 | Docker Compose (app1, app2) |
| Workers per instance | 8 | Gunicorn `-w 8` |
| Threads per worker | 4 | Gunicorn `--threads 4` |
| Total concurrent handlers | 64 | 8 × 4 × 2 instances |
| Database | 1 PostgreSQL instance | Default connection pool |
| Cache | 1 Redis instance | 5-minute TTL |
| Rate limit | 1000 req/min per IP | flask-limiter + Redis backend |

## Where the Bottleneck Is

**PostgreSQL is the bottleneck.** Under heavy load:

1. **List endpoints** (`GET /urls`, `GET /users`) were the first to fail — returning all records per request caused timeouts. **Fixed with pagination** (20 items per page).

2. **Write endpoint** (`POST /shorten`) creates a URL + Event in a transaction. Each write holds a DB connection. At 500 users, write contention spikes. **Mitigated by** Redis-backed rate limiting on writes (500/min).

3. **Redirect endpoint** (`GET /<short_code>`) is the hot path. Without caching, every redirect hits the DB. **Fixed with Redis caching** — subsequent requests for the same short code skip the DB entirely.

## How to Scale Further

### Immediate (no code changes)

| Action | Effect |
|--------|--------|
| Add app3, app4 to docker-compose | Doubles request handlers to 128 |
| Increase gunicorn workers | `-w 16` per container |
| Increase Redis cache TTL | Fewer DB hits on repeated redirects |
| Increase rate limits | Allow more throughput (trade-off: less abuse protection) |

### Medium-term

| Action | Effect |
|--------|--------|
| PostgreSQL connection pooling (PgBouncer) | Handle more concurrent DB connections without overwhelming Postgres |
| PostgreSQL read replicas | Offload read queries to replicas, write to primary |
| Redis cluster | Horizontal cache scaling for higher throughput |

### Long-term (post-hackathon)

| Action | Effect |
|--------|--------|
| Kubernetes + KEDA autoscaling | Auto-scale app pods based on request rate |
| CDN for redirects | Cache 301 responses at the edge — near-zero latency |
| Async event logging (Celery) | Decouple event writes from the redirect response path |
| Database sharding | Split URL table across multiple Postgres instances by short code prefix |

## Cost of Scaling

Current stack runs on a single machine. Estimated resource needs:

| Users | App Instances | RAM | CPU Cores |
|-------|--------------|-----|-----------|
| 50 | 1 | 1 GB | 2 |
| 200 | 2 | 2 GB | 4 |
| 500 | 2-4 | 4 GB | 4-8 |
| 1000+ | 4+ | 8 GB+ | 8+ |

PostgreSQL and Redis each need ~512 MB RAM at current data sizes (400 users, 2000 URLs, 3400 events).
