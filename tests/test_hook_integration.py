"""Tests for hook integration module."""

import json
import os
import pytest
from unittest.mock import AsyncMock, patch

from src.config import RefineConfig, ProviderProfile
from src.hook_integration import (
    build_hook_response,
    extract_prompt_from_hook,
    handle_hook,
    parse_hook_payload,
    _make_accepted_context,
    _make_block_reason,
    _read_pending,
    _write_pending,
    _clear_pending,
    _handle_user_choice,
    _PENDING_FILE,
)


class TestParseHookPayload:
    def test_valid_json(self):
        assert parse_hook_payload('{"prompt": "test"}') == {"prompt": "test"}

    def test_empty_string(self):
        assert parse_hook_payload("") == {}

    def test_invalid_json(self):
        assert parse_hook_payload("not json") == {}


class TestExtractPromptFromHook:
    def test_prompt_field(self):
        assert extract_prompt_from_hook({"prompt": "fix bug", "session_id": "abc"}) == "fix bug"

    def test_missing_prompt(self):
        assert extract_prompt_from_hook({"session_id": "abc"}) == ""


class TestBuildHookResponse:
    def test_with_refined_prompt(self):
        result = build_hook_response("refined", "UserPromptSubmit")
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "refined",
            }
        }

    def test_empty_prompt(self):
        assert build_hook_response("", "UserPromptSubmit") == {}


class TestMakeAcceptedContext:
    def test_includes_prompt_and_approved_marker(self):
        ctx = _make_accepted_context("Goal: Fix bug")
        assert "Goal: Fix bug" in ctx
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Do NOT respond to the selection letter" in ctx


class TestMakeBlockReason:
    def test_includes_a_e_o_s_options(self):
        ctx = _make_block_reason("original", "refined", False)
        assert "a = Accept refined" in ctx
        assert "e = Edit refined" in ctx
        assert "o = Use original" in ctx
        assert "a = Accept refined" in ctx
        assert "original" in ctx
        assert "refined" in ctx

    def test_includes_degraded_note(self):
        ctx = _make_block_reason("orig", "ref", True)
        assert "refinement model was degraded" in ctx.lower()

    def test_no_degraded_note_when_not_degraded(self):
        ctx = _make_block_reason("orig", "ref", False)
        assert "degraded" not in ctx.lower()


class TestPendingFile:
    def setup_method(self):
        _clear_pending()

    def teardown_method(self):
        _clear_pending()

    def test_write_and_read_pending(self):
        _write_pending("original text", "refined text", False)
        pending = _read_pending()
        assert pending is not None
        assert pending["original"] == "original text"
        assert pending["refined"] == "refined text"
        assert pending["degraded"] is False

    def test_read_returns_none_when_no_file(self):
        _clear_pending()
        assert _read_pending() is None

    def test_clear_pending(self):
        _write_pending("orig", "ref", False)
        _clear_pending()
        assert _read_pending() is None
        assert not os.path.exists(_PENDING_FILE)

    def test_read_returns_none_for_invalid_json(self):
        with open(_PENDING_FILE, "w") as f:
            f.write("not json")
        assert _read_pending() is None

    def test_read_returns_none_for_missing_keys(self):
        with open(_PENDING_FILE, "w") as f:
            json.dump({"wrong": "keys"}, f)
        assert _read_pending() is None

    def test_read_returns_none_when_expired(self):
        import time
        _write_pending("orig", "ref", False)
        # Manually backdate the timestamp
        with open(_PENDING_FILE, "r") as f:
            data = json.load(f)
        data["created_at"] = time.time() - 600  # 10 minutes ago
        with open(_PENDING_FILE, "w") as f:
            json.dump(data, f)
        assert _read_pending() is None


class TestHandleUserChoice:
    def setup_method(self):
        _clear_pending()

    def teardown_method(self):
        _clear_pending()

    def test_accept_choice(self):
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        with patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix the bug"):
            result = _handle_user_choice("a", pending, config)
        assert result is not None
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Goal: Fix the bug" in ctx
        assert _read_pending() is None  # pending cleared

    def test_accept_full_word(self):
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        with patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix the bug"):
            result = _handle_user_choice("accept", pending, config)
        assert result is not None
        assert _read_pending() is None

    def test_edit_choice(self):
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        with patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix the bug"):
            result = _handle_user_choice("e", pending, config)
        assert result is not None
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "refined prompt" in ctx.lower()
        assert _read_pending() is None

    def test_original_choice_passes_through(self):
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        result = _handle_user_choice("o", pending, config)
        assert result is None  # pass through
        assert _read_pending() is None

    def test_invalid_choice_reblocks(self):
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        result = _handle_user_choice("x", pending, config)
        assert result is not None
        assert result["decision"] == "block"
        assert "Accept refined" in result["reason"]
        assert _read_pending() is not None  # pending NOT cleared

    def test_multi_char_input_treated_as_new_prompt(self):
        """Multi-character input (not a/e/o/s) is treated as a new prompt, not a choice."""
        pending = {"original": "fix bug", "refined": "Goal: Fix the bug", "degraded": False}
        config = RefineConfig()
        result = _handle_user_choice("你好世界", pending, config)
        assert result is None  # pass through — new prompt
        assert _read_pending() is None  # pending cleared


class TestHandleHook:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_prompt(self):
        assert await handle_hook({"prompt": ""}) is None

    @pytest.mark.asyncio
    async def test_returns_none_for_skip_command(self):
        assert await handle_hook({"prompt": "/no-refine fix this"}) is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_credentials(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        assert await handle_hook({"prompt": "fix the login bug in the app"}, config) is None

    @pytest.mark.asyncio
    async def test_tui_unavailable_blocks_prompt(self, monkeypatch):
        """When terminal is unavailable, block with A/E/O/S comparison."""
        _clear_pending()
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug", False))

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"),
            patch("src.hook_integration.open_terminal_out", return_value=None),
            patch("src.hook_integration.open_terminal_in", return_value=None),
        ):
            result = await handle_hook({"prompt": "fix the login bug in the app"}, config)

        assert result is not None
        assert result["decision"] == "block"
        reason = result["reason"]
        assert "a = Accept refined" in reason
        assert "e = Edit refined" in reason
        assert "o = Use original" in reason
        assert "fix the login bug" in reason
        # Pending file should be written
        assert _read_pending() is not None
        _clear_pending()

    @pytest.mark.asyncio
    async def test_pending_choice_accept(self, monkeypatch):
        """When user resubmits with 'a' after block, return accepted context."""
        _clear_pending()
        _write_pending("fix the login bug", "Goal: Fix login bug", False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()

        with patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"):
            result = await handle_hook({"prompt": "a"}, config)

        assert result is not None
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Goal: Fix login bug" in ctx
        assert _read_pending() is None

    @pytest.mark.asyncio
    async def test_tui_accept_returns_accepted_context(self, monkeypatch):
        """When TUI is available and user accepts, return approved context."""
        _clear_pending()
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug", False))

        from io import StringIO
        term_out = StringIO()
        term_in = StringIO("a\n")  # user presses 'a' for accept

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"),
            patch("src.hook_integration.open_terminal_out", return_value=term_out),
            patch("src.hook_integration.open_terminal_in", return_value=term_in),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is not None
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Goal: Fix login bug" in ctx
        assert "Do NOT respond to the selection letter" in ctx

    @pytest.mark.asyncio
    async def test_tui_original_returns_none(self, monkeypatch):
        """When TUI is available and user chooses original, pass through."""
        _clear_pending()
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug", False))

        from io import StringIO
        term_out = StringIO()
        term_in = StringIO("o\n")  # user presses 'o' for original

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"),
            patch("src.hook_integration.open_terminal_out", return_value=term_out),
            patch("src.hook_integration.open_terminal_in", return_value=term_in),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None  # pass through

    @pytest.mark.asyncio
    async def test_returns_none_on_llm_failure(self, monkeypatch):
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", AsyncMock(side_effect=Exception("fail"))),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_no_change_returns_none(self, monkeypatch):
        """When refined is identical to original, pass through."""
        _clear_pending()
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("fix the login bug", False))

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None
