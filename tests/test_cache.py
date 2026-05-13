"""Tests for cache module."""

import time

import pytest

from src.cache import SummaryCache


class TestSummaryCache:
    def test_put_and_get(self, tmp_path):
        cache = SummaryCache(tmp_path, ttl=300)
        cache.put("transcript1", "summary1")
        assert cache.get("transcript1") == "summary1"

    def test_miss(self, tmp_path):
        cache = SummaryCache(tmp_path, ttl=300)
        assert cache.get("nonexistent") is None

    def test_expired(self, tmp_path):
        cache = SummaryCache(tmp_path, ttl=0)
        cache.put("key", "value")
        time.sleep(0.01)
        assert cache.get("key") is None

    def test_clear(self, tmp_path):
        cache = SummaryCache(tmp_path, ttl=300)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        count = cache.clear()
        assert count == 2
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_persistence(self, tmp_path):
        # Write with one instance
        cache1 = SummaryCache(tmp_path, ttl=300)
        cache1.put("key", "value")

        # Read with another instance
        cache2 = SummaryCache(tmp_path, ttl=300)
        assert cache2.get("key") == "value"
