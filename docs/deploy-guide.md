# Deploy Guide

## Prerequisites

- Docker and Docker Compose (or Podman with docker-compose)
- Git

## Deploy with Docker Compose

```bash
# Clone
git clone https://github.com/parth-gulati/PE-Hackathon-Template-2026.git
cd PE-Hackathon-Template-2026

# Start all services
docker-compose up --build -d

# Fix nginx DNS (required for Podman)
sleep 5
docker-compose restart nginx

# Seed database
docker-compose exec app1 uv run python seed_data.py

# Verify
curl http://localhost/health
```

## Services and Ports

| Service | Port | URL |
|---------|------|-----|
| Nginx (entry point) | 80 | http://localhost |
| Grafana | 3001 | http://localhost:3001 |
| Prometheus | 9090 | http://localhost:9090 |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |

## Configuration

All configuration is via environment variables in `docker-compose.yml`. Override with a `.env` file or shell exports:

```bash
API_KEY=my-production-key docker-compose up -d
```

## Scaling

Add more app instances by duplicating the app service:

```yaml
app3:
  <<: *app-common
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```

Then add `server app3:5000;` to `nginx/nginx.conf` upstream block.

## Rollback

```bash
# Stop current deployment
docker-compose down

# Go back to previous version
git checkout <previous-commit-hash>

# Redeploy
docker-compose up --build -d
sleep 5
docker-compose restart nginx
```

To rollback without losing data (postgres volume persists):
```bash
docker-compose down  # keeps volumes
docker-compose up --build -d
```

To fully reset (destroys data):
```bash
docker-compose down -v  # removes volumes
docker-compose up --build -d
docker-compose exec app1 uv run python seed_data.py
```
