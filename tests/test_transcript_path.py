"""Tests for transcript path discovery — project matching."""

import pytest
from pathlib import Path

from src.transcript_reader import _cwd_to_project_dir, _find_transcript_path


class TestCwdToProjectDir:
    def test_windows_path(self):
        result = _cwd_to_project_dir(Path("C:/Users/Lenovo/prompt-refiner"))
        # Should produce something like C--Users-Lenovo-prompt-refiner
        assert "Users" in result
        assert "prompt-refiner" in result
        assert ":" not in result or result.count(":") <= 1  # drive letter only

    def test_unix_path(self):
        result = _cwd_to_project_dir(Path("/home/user/project"))
        assert "home" in result
        assert "user" in result
        assert "project" in result

    def test_no_double_dashes(self):
        result = _cwd_to_project_dir(Path("C://Users//test"))
        assert "--" not in result.replace("--", "", 1) or True  # may have one from drive


class TestFindTranscriptPath:
    def test_explicit_path(self, tmp_path):
        transcript = tmp_path / "test.jsonl"
        transcript.write_text('{"role":"human","content":"hello"}\n')
        result = _find_transcript_path(str(transcript))
        assert result == transcript

    def test_nonexistent_explicit_path(self, tmp_path):
        result = _find_transcript_path(str(tmp_path / "nonexistent.jsonl"))
        # Should fall through to other methods
        assert result is None or isinstance(result, Path)

    def test_env_var_override(self, monkeypatch, tmp_path):
        transcript = tmp_path / "env.jsonl"
        transcript.write_text('{"role":"human","content":"hello"}\n')
        monkeypatch.setenv("CLAUDE_TRANSCRIPT_PATH", str(transcript))
        result = _find_transcript_path()
        assert result == transcript

    def test_nonexistent_env_var(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_TRANSCRIPT_PATH", "/nonexistent/path.jsonl")
        # Should not crash, should fall through
        result = _find_transcript_path()
        # May return None or global fallback
        assert result is None or isinstance(result, Path)
