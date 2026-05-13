"""Tests for hook_entry module — argument parsing and error handling."""

import json
import pytest

from src.hook_entry import _parse_args


class TestParseArgs:
    def test_default_event(self):
        event, config = _parse_args(["hook_entry.py"])
        assert event == "UserPromptSubmit"
        assert config == ""

    def test_explicit_event(self):
        event, config = _parse_args(["hook_entry.py", "UserPromptExpansion"])
        assert event == "UserPromptExpansion"

    def test_config_flag(self):
        event, config = _parse_args(["hook_entry.py", "--config", "prompt-config.json"])
        assert event == "UserPromptSubmit"
        assert config == "prompt-config.json"

    def test_event_and_config(self):
        event, config = _parse_args(["hook_entry.py", "UserPromptSubmit", "--config", "my.json"])
        assert event == "UserPromptSubmit"
        assert config == "my.json"

    def test_unknown_flags_ignored(self):
        event, config = _parse_args(["hook_entry.py", "--debug"])
        assert event == "UserPromptSubmit"


class TestHookEntryStderr:
    """Test that errors are handled gracefully."""

    def test_invalid_json_produces_no_output(self, capsys):
        """Invalid JSON input should produce no stdout (pass through)."""
        from src.hook_entry import main
        from unittest.mock import patch
        from io import StringIO

        with patch("sys.stdin", StringIO("not json {")):
            with patch("sys.argv", ["hook_entry.py"]):
                main()

        captured = capsys.readouterr()
        assert captured.out == ""
