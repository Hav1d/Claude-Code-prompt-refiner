"""End-to-end tests for hook integration.

Tests the full pipeline: payload → refinement → TUI review → hook output.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from src.config import RefineConfig, ProviderProfile
from src.hook_integration import (
    build_hook_response,
    handle_hook,
    parse_hook_payload,
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


class TestHandleHookEndToEnd:
    """Test handle_hook with mocked LLM and terminal."""

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
    async def test_success_returns_hook_specific_output(self, monkeypatch):
        """Successful refinement should return hookSpecificOutput dict."""
        monkeypatch.setattr("src.credentials._read_claude_config_key", lambda: None)
        config = RefineConfig(
            active_provider="test",
            providers={"test": ProviderProfile(api_key="test-key")},
        )

        mock_refine = AsyncMock(return_value=("Goal: Fix login bug\nContext: REST API", False))

        with (
            patch("src.transcript_reader.read_transcript", return_value=[]),
            patch("src.refiner.refine_prompt", mock_refine),
            patch("src.refiner.apply_prefix_suffix", return_value="Goal: Fix login bug\nContext: REST API"),
        ):
            result = await handle_hook({"prompt": "fix the login bug"}, config)

        assert result is not None
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        ctx = result["hookSpecificOutput"]["additionalContext"]
        assert "Original prompt:" in ctx
        assert "Refined prompt:" in ctx
        assert "Goal: Fix login bug" in ctx
