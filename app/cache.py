"""Redis caching layer for URL lookups."""

import json
import os

import redis

CACHE_TTL = int(os.environ.get("CACHE_TTL", 300))  # 5 minutes default

_client = None


def get_redis():
    """Get or create Redis client. Returns None if Redis is unavailable."""
    global _client
    if _client is not None:
        return _client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        _client = redis.from_url(redis_url, decode_responses=True)
        _client.ping()
        return _client
    except Exception:
        _client = None
        return None


def cache_get(key):
    """Get a value from cache. Returns None on miss or if Redis is down."""
    r = get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def cache_set(key, value, ttl=None):
    """Set a value in cache. Silently fails if Redis is down."""
    r = get_redis()
    if r is None:
        return
    try:
        r.set(key, json.dumps(value), ex=ttl or CACHE_TTL)
    except Exception:
        pass


def cache_delete(key):
    """Delete a key from cache. Silently fails if Redis is down."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass
