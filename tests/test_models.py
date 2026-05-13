"""Tests for data models."""

from src.models import (
    CacheEntry,
    RefineResult,
    SessionContext,
    TranscriptEntry,
    UserChoice,
)
import time


class TestSessionContext:
    def test_empty_context(self):
        ctx = SessionContext()
        assert ctx.to_text() == "(no context)"

    def test_partial_context(self):
        ctx = SessionContext(task="Fix login bug", current_blocker="422 error")
        text = ctx.to_text()
        assert "Task: Fix login bug" in text
        assert "Blocker: 422 error" in text
        assert "Tech stack" not in text

    def test_full_context(self):
        ctx = SessionContext(
            task="Build API",
            tech_stack="Python, FastAPI",
            attempted="Tried X, Y",
            current_blocker="DB connection error",
            modifications="api/routes.py",
            constraints="Must use async",
        )
        text = ctx.to_text()
        assert "Task: Build API" in text
        assert "Constraints: Must use async" in text


class TestRefineResult:
    def test_to_dict(self):
        result = RefineResult(
            original_input="fix bug",
            context_summary="(no context)",
            refined_prompt="Fix the bug in login.py",
            final_prompt="Fix the bug in login.py",
            user_choice=UserChoice.ACCEPT,
            duration_ms=150.5,
        )
        d = result.to_dict()
        assert d["user_choice"] == "accept"
        assert d["duration_ms"] == 150.5
        assert d["error"] is None
        assert d["degraded"] is False


class TestCacheEntry:
    def test_not_expired(self):
        entry = CacheEntry(key="test", summary="sum", ttl=300)
        assert not entry.is_expired()

    def test_expired(self):
        entry = CacheEntry(
            key="test", summary="sum",
            created_at=time.time() - 400, ttl=300,
        )
        assert entry.is_expired()


class TestTranscriptEntry:
    def test_creation(self):
        entry = TranscriptEntry(role="human", content="hello")
        assert entry.role == "human"
        assert entry.content == "hello"
        assert entry.timestamp is None
