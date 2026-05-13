"""Tests for summarizer module."""

import pytest

from src.models import SessionContext, TranscriptEntry
from src.summarizer import _heuristic_summarize, _parse_summary


class TestHeuristicSummarize:
    def test_empty_entries(self):
        ctx = _heuristic_summarize([])
        assert ctx.task == ""

    def test_extracts_task(self):
        entries = [
            TranscriptEntry(role="human", content="Fix the login bug"),
        ]
        ctx = _heuristic_summarize(entries)
        assert "Fix the login bug" in ctx.task

    def test_extracts_error(self):
        entries = [
            TranscriptEntry(role="human", content="fix this"),
            TranscriptEntry(
                role="assistant",
                content="I found the error:\nTypeError: cannot read property 'id' of undefined",
            ),
        ]
        ctx = _heuristic_summarize(entries)
        assert "TypeError" in ctx.current_blocker or "error" in ctx.current_blocker.lower()

    def test_extracts_modifications(self):
        entries = [
            TranscriptEntry(role="assistant", content="Created src/app.py\nModified src/utils.py"),
        ]
        ctx = _heuristic_summarize(entries)
        assert "Created" in ctx.modifications or "Modified" in ctx.modifications


class TestParseSummary:
    def test_parse_standard_format(self):
        text = """Task: Fix login bug
Tech stack: Python, FastAPI
Blocker: 422 Unprocessable Entity"""
        ctx = _parse_summary(text)
        assert ctx.task == "Fix login bug"
        assert ctx.tech_stack == "Python, FastAPI"
        assert "422" in ctx.current_blocker

    def test_parse_empty(self):
        ctx = _parse_summary("")
        assert ctx.task == ""

    def test_parse_unknown_fields_ignored(self):
        text = "Task: Build API\nUnknown: something"
        ctx = _parse_summary(text)
        assert ctx.task == "Build API"
