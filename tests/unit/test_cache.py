"""Unit tests for cache module — tests graceful degradation without Redis."""

from unittest.mock import patch

from app.cache import cache_delete, cache_get, cache_set, get_redis
import app.cache as cache_module


class TestCacheWithoutRedis:
    """When REDIS_URL is not set, cache operations should silently no-op."""

    def setup_method(self):
        cache_module._client = None

    @patch.dict("os.environ", {}, clear=True)
    def test_get_redis_returns_none_without_url(self):
        cache_module._client = None
        assert get_redis() is None

    @patch.dict("os.environ", {}, clear=True)
    def test_cache_get_returns_none(self):
        cache_module._client = None
        assert cache_get("nonexistent") is None

    @patch.dict("os.environ", {}, clear=True)
    def test_cache_set_does_not_raise(self):
        cache_module._client = None
        cache_set("key", {"value": 1})  # should not raise

    @patch.dict("os.environ", {}, clear=True)
    def test_cache_delete_does_not_raise(self):
        cache_module._client = None
        cache_delete("key")  # should not raise


class TestCacheWithBadRedis:
    """When Redis URL is set but unreachable, cache should degrade gracefully."""

    def setup_method(self):
        cache_module._client = None

    @patch.dict("os.environ", {"REDIS_URL": "redis://localhost:19999/0"})
    def test_get_redis_returns_none_on_connection_error(self):
        cache_module._client = None
        assert get_redis() is None

    @patch.dict("os.environ", {"REDIS_URL": "redis://localhost:19999/0"})
    def test_cache_get_returns_none_on_bad_connection(self):
        cache_module._client = None
        assert cache_get("key") is None
