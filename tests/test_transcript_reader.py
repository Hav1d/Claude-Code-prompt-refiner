"""Tests for transcript reader module."""

import json

import pytest

from src.models import TranscriptEntry
from src.transcript_reader import (
    _extract_content,
    format_transcript_for_context,
    read_transcript,
)


class TestExtractContent:
    def test_string_content(self):
        assert _extract_content({"content": "hello"}) == "hello"

    def test_list_content_text_blocks(self):
        data = {
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": "World"},
            ]
        }
        assert "Hello" in _extract_content(data)
        assert "World" in _extract_content(data)

    def test_empty_content(self):
        assert _extract_content({"content": ""}) == ""
        assert _extract_content({}) == ""

    def test_tool_result_truncated(self):
        data = {
            "content": [
                {"type": "tool_result", "content": "x" * 500},
            ]
        }
        result = _extract_content(data)
        assert "..." in result


class TestFormatTranscriptForContext:
    def test_basic_format(self):
        entries = [
            TranscriptEntry(role="human", content="fix the bug"),
            TranscriptEntry(role="assistant", content="I'll fix it"),
        ]
        result = format_transcript_for_context(entries)
        assert "[User]" in result
        assert "[Assistant]" in result

    def test_truncation(self):
        entries = [
            TranscriptEntry(role="human", content="x" * 1000),
        ]
        result = format_transcript_for_context(entries, max_chars=100)
        assert len(result) <= 100 + 50  # some tolerance for prefix

    def test_empty(self):
        assert format_transcript_for_context([]) == ""


class TestReadTranscript:
    def test_read_from_file(self, tmp_path):
        transcript_file = tmp_path / "transcript.jsonl"
        entries = [
            {"role": "human", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        transcript_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )
        result = read_transcript(max_entries=10, explicit_path=str(transcript_file))
        assert len(result) == 2
        assert result[0].role == "human"
        assert result[1].role == "assistant"

    def test_max_entries(self, tmp_path):
        transcript_file = tmp_path / "transcript.jsonl"
        entries = [{"role": "human", "content": f"msg {i}"} for i in range(20)]
        transcript_file.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )
        result = read_transcript(max_entries=5, explicit_path=str(transcript_file))
        assert len(result) == 5

    def test_nonexistent_file_falls_back(self):
        """When explicit path doesn't exist, falls back to project directory."""
        result = read_transcript(max_entries=10, explicit_path="/nonexistent/path")
        # May find real transcripts via fallback — just verify it doesn't crash
        assert isinstance(result, list)
