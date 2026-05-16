"""End-to-end tests for hook integration.

Tests the full pipeline: payload -> refinement -> TUI review -> hook output.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from src.config import RefineConfig, ProviderProfile
from src.hook_integration import (
    build_hook_response,
    handle_hook,
    parse_hook_payload,
    _make_accepted_context,
    _make_block_reason,
    _write_pending,
    _clear_pending,
    _read_pending,
)


class TestHookOutputFormat:
    """Verify hook output matches Claude Code's expected format."""

    def test_success_format(self):
        result = build_hook_response("refined prompt", "UserPromptSubmit")
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert result["hookSpecificOutput"]["additionalContext"] == "refined prompt"

    def test_empty_returns_empty_dict(self):
        result = build_hook_response("", "UserPromptSubmit")
        assert result == {}

    def test_format_with_prefix_suffix(self):
        """Prefix/suffix should be included in additionalContext."""
        result = build_hook_response("Be concise.\n\nfix the bug\n\nUse Python.", "UserPromptSubmit")
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "Be concise." in ctx
        assert "fix the bug" in ctx
        assert "Use Python." in ctx


class TestAcceptedContext:
    def test_user_approved_marker(self):
        ctx = _make_accepted_context("Goal: Fix bug")
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Goal: Fix bug" in ctx
        assert "Do NOT respond to the selection letter" in ctx


class TestBlockReason:
    def test_all_four_options_present(self):
        ctx = _make_block_reason("orig", "refined", False)
        assert "a = Accept refined" in ctx
        assert "e = Edit refined" in ctx
        assert "o = Use original" in ctx
        assert "a = Accept refined" in ctx

    def test_includes_comparison(self):
        ctx = _make_block_reason("orig", "refined", False)
        assert "orig" in ctx
        assert "refined" in ctx

    def test_degraded_state(self):
        ctx = _make_block_reason("orig", "ref", True)
        assert "refinement model was degraded" in ctx.lower()


class TestHandleHookEndToEnd:
    """Test handle_hook with mocked LLM and terminal."""

    def setup_method(self):
        _clear_pending()

    def teardown_method(self):
        _clear_pending()

    @pytest.mark.asyncio
    async def test_skip_command_returns_none(self):
        result = await handle_hook({"prompt": "/no-refine fix this"})
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_prompt_returns_none(self):
        result = await handle_hook({"prompt": ""})
        assert result is None

    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()
        result = await handle_hook({"prompt": "fix the login bug"}, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self, monkeypatch):
        """When LLM fails, hook should return None (pass through), not crash."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", AsyncMock(side_effect=Exception("LLM down"))),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_tui_unavailable_blocks_prompt(self, monkeypatch):
        """When TUI is unavailable, block with A/E/O/S comparison."""
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug\nContext: REST API", False))

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"),
            patch("src.hook_integration.open_terminal_out", return_value=None),
            patch("src.hook_integration.open_terminal_in", return_value=None),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is not None
        assert result["decision"] == "block"
        reason = result["reason"]
        assert "a = Accept refined" in reason
        assert "e = Edit refined" in reason
        assert "o = Use original" in reason
        assert "fix the login bug" in reason
        assert "Goal: Fix login bug" in reason
        # Pending file should be written
        assert _read_pending() is not None

    @pytest.mark.asyncio
    async def test_pending_choice_accept(self, monkeypatch):
        """User resubmits 'a' after block -> accepted context."""
        _write_pending("fix the login bug", "Goal: Fix login bug", False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()

        with patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug"):
            result = await handle_hook({"prompt": "a"}, config)

        assert result is not None
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "PROMPT-REFINER: USER APPROVED" in ctx
        assert "Goal: Fix login bug" in ctx

    @pytest.mark.asyncio
    async def test_pending_choice_original(self, monkeypatch):
        """User resubmits 'o' after block -> pass through."""
        _write_pending("fix the login bug", "Goal: Fix login bug", False)
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig()

        result = await handle_hook({"prompt": "o"}, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_tui_accept_returns_approved_context(self, monkeypatch):
        """When TUI is available and user accepts, get approved context."""
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug", False))

        from io import StringIO
        term_out = StringIO()
        term_in = StringIO("a\n")

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

    @pytest.mark.asyncio
    async def test_tui_original_passes_through(self, monkeypatch):
        """When TUI is available and user chooses original, pass through."""
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Refined version", False))

        from io import StringIO
        term_out = StringIO()
        term_in = StringIO("o\n")

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Refined version"),
            patch("src.hook_integration.open_terminal_out", return_value=term_out),
            patch("src.hook_integration.open_terminal_in", return_value=term_in),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is None  # pass through
